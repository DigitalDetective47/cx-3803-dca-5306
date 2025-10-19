import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';


const TRUCK_LENGTH = 53;
const TRUCK_HEIGHT = 8.5;
const TRUCK_WIDTH = 9;
// Store items in the scene
const items = new Map();

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.set(80, 25, 40);
camera.lookAt(0, 5, 0);

// Renderer setup
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('scene') });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0xeeeeee);
renderer.shadowMap.enabled = true;

// Lighting
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(5, 5, 5);
scene.add(light);

// Add a ground plane
const plane = new THREE.Mesh(
  new THREE.PlaneGeometry(100000, 100000),
  new THREE.MeshStandardMaterial({ color: 0xaaaaaa })
);
plane.rotation.x = -Math.PI / 2;
scene.add(plane);

// Add a truck
const truckGeometry = new THREE.BoxGeometry(TRUCK_LENGTH, TRUCK_HEIGHT, TRUCK_WIDTH);
const truckMaterial = new THREE.MeshBasicMaterial({
  color: 0x222222,
  transparent: true,
  opacity: 0.2,
});

// Create truck mesh
const truck = new THREE.Mesh(truckGeometry, truckMaterial);
truckGeometry.translate(TRUCK_LENGTH / 2, TRUCK_HEIGHT / 2 , -TRUCK_WIDTH / 2);
// truck.position.y = 8.5 / 2 + 0.5;
scene.add(truck);

const edges = new THREE.EdgesGeometry(truckGeometry);
const outline = new THREE.LineSegments(
  edges,
  new THREE.LineBasicMaterial({ color: 0x000000 })
);
truck.add(outline);

// Controls (click + drag)
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI / 2.1;
controls.minDistance = 10;  
controls.maxDistance = 100;


// Resize support
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Function to add item to 3D scene
function addItemToScene(item) {
  // Random color for each item
  const color = new THREE.Color(Math.random(), Math.random(), Math.random());

  // Create box geometry for the item
  const geometry = new THREE.BoxGeometry(item.x_size / 12, item.y_size / 12, item.z_size / 12);
  const material = new THREE.MeshStandardMaterial({
    color: color,
    transparent: true,
    opacity: 0.8
  });

  const mesh = new THREE.Mesh(geometry, material);

  // Position items outside the trailer
  const existingItemsCount = items.size;
  const offsetX = 1.5 * TRUCK_LENGTH + (existingItemsCount % 3) * 8; 
  const offsetY = item.y_size / 2 + 2; 
  const offsetZ = Math.floor(existingItemsCount / 3) * 6 - 6;

  mesh.position.set(offsetX, offsetY, offsetZ);
  mesh.userData.originalPos = mesh.position.clone();
  // Add edges for better visibility
  const edges = new THREE.EdgesGeometry(geometry);
  const outline = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x000000 })
  );
  mesh.add(outline);

  scene.add(mesh);
  items.set(item.id, mesh);

  return mesh;
}



// Function to load all existing items for current simulation
async function loadItems() {
  try {
    // Build URL with simulation filter if available
    let url = '/api/get-items/';
    if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
      url += `?simulation_id=${SIMULATION_ID}`;
    }

    const response = await fetch(url);
    const data = await response.json();

    if (data.success) {
      data.items.forEach(item => {
        if (!items.has(item.id)) {
          addItemToScene(item);
        }
      });
    }
  } catch (error) {
    console.error('Error loading items:', error);
  }
}



let toBeLoadedItems = []; // store items with their target positions

async function loadItemsForAnimation() {
    try {
        let url = '/api/get-simplacements/';
        if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
            url += `?simulation_id=${SIMULATION_ID}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            // console.log("Fetched placements:", data.items);

            // Step 1: build array of existing items with their target positions
            toBeLoadedItems = data.items
                .filter(item => items.has(item.hu_id)) // match by hu_id since that's your object key
                .map(item => {
                    const mesh = items.get(item.hu_id);
                    const halfX = (mesh.geometry.parameters.width ?? 0) / 2;
                    const halfY = (mesh.geometry.parameters.height ?? 0) / 2;
                    const halfZ = (mesh.geometry.parameters.depth ?? 0) / 2;
                    return {
                        id: item.hu_id,
                        mesh: mesh,
                        targetPos: new THREE.Vector3(
                            (item.dest_x_coord + halfX * 12) / 12, // add half-width to move to center
                            (item.dest_y_coord + halfY * 12) / 12, // add half-height to move to center
                            (item.dest_z_coord - halfZ * 12) / 12
                        ),
                        x_coord: item.dest_x_coord,
                        y_coord: item.dest_y_coord,
                        z_coord: item.dest_z_coord
                    };
                })
                // Step 2: sort by loading order: back → left → bottom
                .sort((a, b) => {
                    if (a.x_coord !== b.x_coord) return a.x_coord - b.x_coord; // back to front
                    if (a.y_coord !== b.y_coord) return a.y_coord - b.y_coord; // top to bottom
                    // if (a.z_coord !== b.z_coord) return a.z_coord - b.z_coord; // left to right
                    //flipped because z-coord is negative
                    return -(a.z_coord - b.z_coord); // bottom to top
                });
        }

        // console.log("Prepared toBeLoadedItems:", toBeLoadedItems);
    } catch (error) {
        console.error('Error loading items for animation:', error);
    }
}




let animQueue = [];
let animSpeed = 0.05; // units per frame


function animateItemsSequentially() {
    if (0 == animQueue.length) return;

    //get head of queue
    const meshObj = animQueue[0];
    const mesh = meshObj.mesh;
    const target = meshObj.targetPos;

    const delta = target.clone().sub(mesh.position);
    if (delta.length() < 0.01) {
        mesh.position.copy(target);
        animQueue.shift();
        if (animQueue.length === 0) {
            isAnimating = false;
            isResetMode = true;
            animateBtn.textContent = 'Reset';
        }
    } else {
        mesh.position.lerp(target, animSpeed);
        isResetMode = true;
        animateBtn.textContent = 'Reset';
    }
}

function startAnimation() {
    animQueue = toBeLoadedItems.map(item => ({
        mesh: items.get(item.id),
        targetPos: item.targetPos,
        done: false
    }));
}

const animateBtn = document.getElementById('animate-btn');

animateBtn.addEventListener('click', async () => {

    if (isResetMode) {
      toBeLoadedItems.forEach(item => {
        const mesh = items.get(item.id);
        if (mesh && mesh.userData.originalPos) {
          mesh.position.copy(mesh.userData.originalPos);
        }
      });
      isResetMode = false;
      isAnimating = false;
      animateBtn.textContent = 'Animate';
      return;
    }

    await loadItemsForAnimation();
    // Reset all items to their original positions
    toBeLoadedItems.forEach(item => {
        const mesh = items.get(item.id);
        if (mesh && mesh.userData.originalPos) {
            mesh.position.copy(mesh.userData.originalPos);
        }
    });

    // Rebuild the animation queue and start animation
    startAnimation();
    if (animQueue.length > 0) {
      isAnimating = true;
    }

});


// Handle add item form submission
document.getElementById('add-item-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());

  // Add simulation ID if available
  if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
    data.simulation_id = SIMULATION_ID;
  }

  const messageEl = document.getElementById('message');

  try {
    const response = await fetch('/api/add-item/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      // Show success message
      messageEl.textContent = result.message;
      messageEl.className = 'message success';
      messageEl.style.display = 'block';

      // Add item to 3D scene
      addItemToScene(result.item);

      // Reset form
      e.target.reset();

      // Hide message after 3 seconds
      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    } else {
      // Show error message
      messageEl.textContent = result.message;
      messageEl.className = 'message error';
      messageEl.style.display = 'block';
    }
  } catch (error) {
    messageEl.textContent = 'Error adding item. Please try again.';
    messageEl.className = 'message error';
    messageEl.style.display = 'block';
  }
});




const ALLOWED_ROTATIONS = ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"];
// Handle "Set Position" form submission
document.getElementById('set-pos-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());
  // Fill null/blank orientation with default
  if (!data.orientation) {
    data.orientation = "XYZ";
  }

  if (!ALLOWED_ROTATIONS.includes(data.orientation)) {
    const messageEl = document.getElementById('set-pos-message');
    messageEl.textContent = `Invalid orientation. Allowed values: ${ALLOWED_ROTATIONS.join(", ")}`;
    messageEl.className = 'message error';
    messageEl.style.display = 'block';
    return; // stop submission
  }



  // Add simulation ID if available
  if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
    data.simulation_id = SIMULATION_ID;
  }

  const messageEl = document.getElementById('set-pos-message');

  try {
    const response = await fetch('/api/set-sim-position/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      // Show success message
      messageEl.textContent = result.message;
      messageEl.className = 'message success';
      messageEl.style.display = 'block';

      // Update the item in the 3D scene
      // const item = result.item;
      // const mesh = items.get(item.id);
      // if (mesh) {
      //   mesh.position.set(item.x_pos, item.y_pos, item.z_pos);
      // }

      // Reset form
      e.target.reset();

      // Hide message after 3 seconds
      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    } else {
      // Show error message
      messageEl.textContent = result.message;
      messageEl.className = 'message error';
      messageEl.style.display = 'block';
    }
  } catch (error) {
    messageEl.textContent = 'Error setting position. Please try again.';
    messageEl.className = 'message error';
    messageEl.style.display = 'block';
  }
});




// Toggle panel functionality
const addToggleBtn = document.getElementById('add-toggle-panel-btn');
const setPosToggleBtn = document.getElementById('set-pos-toggle-btn');
const addPanel = document.getElementById('ui-panel');
const setPosPanel = document.getElementById('set-pos-ui-panel');
let isAddPanelOpen = false;

// Helper to open one panel and close the other
function togglePanel(btn, panel, otherBtn, otherPanel, label) {
  const isOpen = !panel.classList.contains('collapsed');

  if (isOpen) {
    // Close current
    panel.classList.add('collapsed');
    btn.classList.remove('panel-open');
    btn.textContent = label;
    otherBtn.style.display = 'flex';
    animateBtn.style.display = 'flex';
  } else {
    // Open current
    panel.classList.remove('collapsed');
    btn.classList.add('panel-open');
    btn.textContent = '×';

    // Close the other panel if open
    otherPanel.classList.add('collapsed');
    otherBtn.classList.remove('panel-open');
    otherBtn.textContent = otherBtn.dataset.defaultLabel || otherBtn.textContent;
    otherBtn.style.display = 'none';
    animateBtn.style.display = 'none';
  }
}

// Store default labels (for when reopening)
addToggleBtn.dataset.defaultLabel = 'Add New Item';
setPosToggleBtn.dataset.defaultLabel = 'Set Item Position';

// Add listeners
addToggleBtn.addEventListener('click', () => {
  togglePanel(addToggleBtn, addPanel, setPosToggleBtn, setPosPanel, 'Add New Item');
});

setPosToggleBtn.addEventListener('click', () => {
  togglePanel(setPosToggleBtn, setPosPanel, addToggleBtn, addPanel, 'Set Item Position');
});

// Load existing items on page load
loadItems();

let isAnimating = false;
let isResetMode = false
// Animation loop
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  if (isAnimating){
    animateItemsSequentially();
  }
  renderer.render(scene, camera);
  
}

animate();