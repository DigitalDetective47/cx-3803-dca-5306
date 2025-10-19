import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

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
const truckGeometry = new THREE.BoxGeometry(53, 8.5, 9);
const truckMaterial = new THREE.MeshBasicMaterial({
  color: 0x222222,
  transparent: true,
  opacity: 0.2,
});

// Create truck mesh
const truck = new THREE.Mesh(truckGeometry, truckMaterial);
truck.position.y = 8.5 / 2 + 0.5;
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

  // Position items outside the trailer (floating, waiting for simulation)
  // Items will be arranged next to the truck
  const existingItemsCount = items.size;
  const offsetX = -40 - (existingItemsCount % 3) * 8;  // Next to truck
  const offsetY = item.y_size / 2 + 2;  // Slightly elevated
  const offsetZ = Math.floor(existingItemsCount / 3) * 6 - 6;

  mesh.position.set(offsetX, offsetY, offsetZ);

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

// Handle form submission
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

// Toggle panel functionality
const toggleBtn = document.getElementById('toggle-panel-btn');
const uiPanel = document.getElementById('ui-panel');
let isPanelOpen = false;

toggleBtn.addEventListener('click', () => {
  isPanelOpen = !isPanelOpen;

  if (isPanelOpen) {
    uiPanel.classList.remove('collapsed');
    toggleBtn.classList.add('panel-open');
    toggleBtn.textContent = '×';
  } else {
    uiPanel.classList.add('collapsed');
    toggleBtn.classList.remove('panel-open');
    toggleBtn.textContent = 'Add New Item';
  }
});

// Click to select
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let selectedItem = null;

renderer.domElement.addEventListener('click', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();

  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);

  const intersects = raycaster.intersectObjects(Array.from(items.values()), true);

  if (intersects.length > 0) {
    let mesh = intersects[0].object;
    while (!items.has([...items].find(([id, m]) => m === mesh)?.[0])) {
      mesh = mesh.parent;
      if (!mesh) break;
    }

    if (!mesh) return;

    if (selectedItem && selectedItem.material?.emissive) {
      selectedItem.material.emissive.set(0x000000);
    }

    selectedItem = mesh;
    if (selectedItem.material?.emissive) {
      selectedItem.material.emissive.set(0x00ff00);
    }

    console.log("Selected Item:", selectedItem.id || "(no id)");
  } else {
    if (selectedItem && selectedItem.material?.emissive) {
      selectedItem.material.emissive.set(0x000000);
    }
    selectedItem = null;
  }
});



window.deleteSelectedItem = async function() {
  try {
    if (!selectedItem) {
      throw new Error("No item selected");
    }

    // Get the item ID from current map
    const itemId = [...items.entries()].find(([_, mesh]) => mesh === selectedItem)?.[0];
    if (!itemId) {
      throw new Error("Could not find item ID");
    }

    // Send delete request to backend
    const response = await fetch(`/api/delete-item/${itemId}/`, {
      method: 'DELETE'
    });

    const result = await response.json();

    if (result.success) {
      // Remove from 3D scene
      scene.remove(selectedItem);
      items.delete(itemId);
      selectedItem = null;
      showUserMessage(result.message, "success");
    } else {
      showUserMessage(result.message || "Failed to delete item.", "error");
    }

  } catch (err) {
    showUserMessage(err.message, "error");
  } finally {
    document.getElementById('delete-modal').classList.remove('show');
  }
};

function showUserMessage(msg, type) {
  const globalMessageEl = document.getElementById('global-message');
  globalMessageEl.textContent = msg;
  globalMessageEl.className = `global-message ${type}`;
  globalMessageEl.style.display = "block";

  setTimeout(() => {
    globalMessageEl.style.display = "none";
  }, 4000);
}

// Load existing items on page load
// TODO: Uncomment this when algorithm is ready to properly place items in the truck
// Currently commented out to prevent items from scattering around the scene
loadItems();

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();