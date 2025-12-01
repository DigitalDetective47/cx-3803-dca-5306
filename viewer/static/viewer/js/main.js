import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';


const TRUCK_LENGTH = 53;
const TRUCK_HEIGHT = 8.5;
const TRUCK_WIDTH = 9;
// Store items in the scene
const items = new Map();

const DEFAULT_STOP_COLOR = '#9ca3af';
let STOP_COLOR_MAP = {};

// Prefer backend color; fall back to map/default
function getColorForStop(item) {
  const backendColor = (item.color || '').trim();
  if (backendColor) return backendColor;

  const stop = String(item.stop || '').trim();
  if (!stop) return DEFAULT_STOP_COLOR;
  return STOP_COLOR_MAP[stop] || DEFAULT_STOP_COLOR;
}

function buildStopColorMap(items) {
  const map = {};

  for (const item of items) {
    const stop = String(item.stop || '').trim();
    if (!stop) continue;

    const color = (item.color || '').trim() || DEFAULT_STOP_COLOR;

    if (!map[stop]) {
      map[stop] = color;
    }
  }

  STOP_COLOR_MAP = map;
}



function updateStopLegend() {
  const legendEl = document.getElementById('stop-legend');
  if (!legendEl) return;

  const entries = Object.entries(STOP_COLOR_MAP).sort(
    ([a], [b]) => a.localeCompare(b)
  );

  if (!entries.length) {
    legendEl.innerHTML = '<p class="legend-empty">No stops loaded yet</p>';
    return;
  }

  legendEl.innerHTML = entries.map(([stop, color]) => `
    <div class="legend-row">
      <span class="legend-color" style="background:${color};"></span>
      <span class="legend-label">Stop ${stop}</span>
    </div>
  `).join('');
}



const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdcdcdc);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.set(80, 25, 40);
camera.lookAt(0, 5, 0);

// Renderer setup
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('scene') });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 1);
scene.add(ambientLight);


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

const truckCenter = new THREE.Vector3(
  TRUCK_LENGTH / 2,
  TRUCK_HEIGHT / 2,
  -TRUCK_WIDTH / 2
);

// Controls (click + drag)
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 10;  
controls.maxDistance = 100;
controls.target.copy(truckCenter);
controls.update();


// Resize support
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Function to add item to 3D scene
function addItemToScene(item) {
  const color = getColorForStop(item);


  const geometry = new THREE.BoxGeometry(
    item.x_size / 12,
    item.y_size / 12,
    item.z_size / 12
  );
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



async function loadItems() {
  try {
    let url = '/api/get-items/';
    if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
      url += `?simulation_id=${SIMULATION_ID}`;
    }

    const response = await fetch(url);
    const data = await response.json();

const itemsList = data.items || [];

buildStopColorMap(itemsList);
updateStopLegend();

if (data.success) {
  itemsList.forEach(item => {
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
  if (animationState !== "PLAYING" || animQueue.length === 0) {
        if (animQueue.length === 0 && animationState === "PLAYING") {
            // We just finished the last item
            animationState = "FINISHED";
            animateBtn.textContent = 'Reset';
        }
        return;
    }
    // Get head of queue
    const meshObj = animQueue[0];
    const mesh = meshObj.mesh;
    const target = meshObj.targetPos;

    // Check distance and snap/lerp
    if (mesh.position.distanceTo(target) < 0.01) {
        mesh.position.copy(target);
        
        // *** MODIFIED: Move item from 'to-do' to 'done' stack ***
        const finishedItem = animQueue.shift(); // Remove from 'to-do'
        loadedQueue.push(finishedItem);      // Add to 'done' stack

        // Check if that was the last item
        if (animQueue.length === 0) {
            animationState = "FINISHED";
            animateBtn.textContent = 'Reset';
        }
    } else {
        mesh.position.lerp(target, animSpeed);
    }



    // if (0 == animQueue.length) return;

    // //get head of queue
    // const meshObj = animQueue[0];
    // const mesh = meshObj.mesh;
    // const target = meshObj.targetPos;

    // const delta = target.clone().sub(mesh.position);
    // if (delta.length() < 0.01) {
    //     mesh.position.copy(target);
    //     animQueue.shift();
    //     if (animQueue.length === 0) {
    //         isAnimating = false;
    //         isResetMode = true;
    //         animateBtn.textContent = 'Reset';
    //     }
    // } else {
    //     mesh.position.lerp(target, animSpeed);
    //     isResetMode = true;
    //     animateBtn.textContent = 'Reset';
    // }
}


/**
 * Animates the 'rewindItem' back to its original starting position.
 */
function animateRewind() {
    if (!rewindItem) return;

    const mesh = rewindItem.mesh;
    const target = rewindItem.originalPos; // Rewind to the start

    if (mesh.position.distanceTo(target) < 0.05) {
        mesh.position.copy(target);
        rewindItem = null; // We are done rewinding this item
        // The animation is now in a "PAUSED" state
    } else {
        // Move back to the original position
        mesh.position.lerp(target, animSpeed);
    }
}


function startAnimation() {
    animQueue = toBeLoadedItems.map(item => ({
        id: item.id,
        mesh: items.get(item.id),
        targetPos: item.targetPos,
        originalPos: items.get(item.id).userData.originalPos.clone(),
        done: false
    }));
    loadedQueue = [];
}

const animateBtn = document.getElementById('animate-btn');

animateBtn.addEventListener('click', async () => {
    
    // Logic from previous fix: We want the "Resume" to interrupt the rewind
    // (This part is unchanged from the last version I gave you)

    switch (animationState) {
        case "STOPPED":
            // --- This is the "Animate" logic ---
            await loadItemsForAnimation();
            
            // Reset all items to their original positions
            toBeLoadedItems.forEach(item => {
                const mesh = items.get(item.id);
                if (mesh && mesh.userData.originalPos) {
                    mesh.position.copy(mesh.userData.originalPos);
                }
            });

            startAnimation(); // Build the queue
            if (animQueue.length > 0) {
                animationState = "PLAYING";
                animateBtn.textContent = 'Pause';
            }
            break;

        case "PLAYING":
            // --- This is the "Pause" logic ---
            animationState = "PAUSED";
            animateBtn.textContent = 'Resume';
            break;

        case "PAUSED":
            // --- This is the "Resume" logic ---
            
            // *** FIX: If resuming while rewinding, snap back and stop rewind ***
            if (rewindItem) {
                rewindItem.mesh.position.copy(rewindItem.originalPos);
                rewindItem = null;
            }

            animationState = "PLAYING";
            animateBtn.textContent = 'Pause';
            break;

        case "FINISHED":
            // --- This is the "Reset" logic ---
            toBeLoadedItems.forEach(item => {
                const mesh = items.get(item.id);
                if (mesh && mesh.userData.originalPos) {
                    mesh.position.copy(mesh.userData.originalPos);
                }
            });
            animationState = "STOPPED";
            animateBtn.textContent = 'Animate';
            // Queues are cleared in startAnimation() on next play
            break;
    }
});



const rewindBtn = document.getElementById('rewind-btn');

rewindBtn.addEventListener('click', () => {
    
    // 1. If a rewind is already in progress, snap it to finish
    //    so we can start the next one.
    if (rewindItem) {
        rewindItem.mesh.position.copy(rewindItem.originalPos);
        rewindItem = null;
    }

    // 2. Store the state *before* we change it.
    const wasPlaying = (animationState === "PLAYING");
    const wasFinished = (animationState === "FINISHED");

    // 3. Set the state to PAUSED (if it wasn't already stopped).
    if (wasPlaying || wasFinished) {
        animationState = "PAUSED";
        animateBtn.textContent = 'Resume';
    }

    // 4. Decide *what* to rewind based on the *previous* state.
    
    // *** NEW FIX: Logic to handle both "pause-rewind" and "multi-rewind" ***
    
    let itemInProgress = null;
    if (animQueue.length > 0) {
        itemInProgress = animQueue[0];
    }

    // Check if we should rewind the item-in-progress, or the last completed one.
    // We rewind the item-in-progress IF:
    // 1. We were playing (wasPlaying) OR we were paused (animationState === "PAUSED")
    // 2. AND That item is NOT already at its original position (this avoids the multi-rewind loop)
    if (itemInProgress && 
        !itemInProgress.mesh.position.equals(itemInProgress.originalPos) &&
        (wasPlaying || animationState === "PAUSED")) 
    {
        // This handles both "rewind while playing" and "rewind while paused" (your original bug)
        rewindItem = itemInProgress;
    } 
    // Otherwise, grab the last *completed* item from the stack.
    // This handles "finished" and "multi-rewind" cases (the bug I introduced)
    else if (loadedQueue.length > 0) {
        // Take item off 'done' stack
        rewindItem = loadedQueue.pop(); 
        // Add it back to the front of the 'to-do' queue
        animQueue.unshift(rewindItem);   
    }
    // If queues are empty, nothing happens.
});

// const animateBtn = document.getElementById('animate-btn');

// animateBtn.addEventListener('click', async () => {

//     if (isResetMode) {
//       toBeLoadedItems.forEach(item => {
//         const mesh = items.get(item.id);
//         if (mesh && mesh.userData.originalPos) {
//           mesh.position.copy(mesh.userData.originalPos);
//         }
//       });
//       isResetMode = false;
//       isAnimating = false;
//       animateBtn.textContent = 'Animate';
//       return;
//     }

//     await loadItemsForAnimation();
//     // Reset all items to their original positions
//     toBeLoadedItems.forEach(item => {
//         const mesh = items.get(item.id);
//         if (mesh && mesh.userData.originalPos) {
//             mesh.position.copy(mesh.userData.originalPos);
//         }
//     });

//     // Rebuild the animation queue and start animation
//     startAnimation();
//     if (animQueue.length > 0) {
//       isAnimating = true;
//     }

// });


// Handle add item form submission
document.getElementById('add-item-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());

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
      messageEl.textContent = result.message;
      messageEl.className = 'message success';
      messageEl.style.display = 'block';

      addItemToScene(result.item);

      

      e.target.reset();

      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    } else {
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




// Handle set restrictions form submission
document.getElementById('set-res-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());

  if (typeof SIMULATION_ID !== 'undefined' && SIMULATION_ID !== null && SIMULATION_ID !== 'null') {
    data.simulation_id = SIMULATION_ID;
  }

  const messageEl = document.getElementById('message');

  try {
    const response = await fetch('/api/set-restrictions/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      messageEl.textContent = result.message;
      messageEl.className = 'message success';
      messageEl.style.display = 'block';

      e.target.reset();

      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    } else {
      messageEl.textContent = result.message;
      messageEl.className = 'message error';
      messageEl.style.display = 'block';
    }
  } catch (error) {
    messageEl.textContent = 'Error setting restrictions. Please try again.';
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
      messageEl.textContent = result.message;
      messageEl.className = 'message success';
      messageEl.style.display = 'block';

      // Update the item in the 3D scene
      // const item = result.item;
      // const mesh = items.get(item.id);
      // if (mesh) {
      //   mesh.position.set(item.x_pos, item.y_pos, item.z_pos);
      // }

      e.target.reset();

      setTimeout(() => {
        messageEl.style.display = 'none';
      }, 3000);
    } else {
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



const runBtn = document.getElementById("runAlgoButton");
if (runBtn) {
  runBtn.addEventListener("click", async () => {
    console.log("Run Algo button clicked. SIMULATION_ID =", SIMULATION_ID);

    if (!SIMULATION_ID) {
      console.error("No SIMULATION_ID available.");
      showUserMessage("No simulation selected.", "error");
      return;
    }

    showUserMessage("Running algorithm...", "info");

    try {
      const res = await fetch(`/api/run-algo/${SIMULATION_ID}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // body can be omitted since the view reads from URL path
        // body: JSON.stringify({}),
      });

      console.log("HTTP status:", res.status);

      // make sure we can still read JSON once
      const data = await res.json();

      console.log("Run algo response:", data);

      if (res.ok && data.status === "ok") {
        showUserMessage("Algorithm ran successfully!", "success");
        setTimeout(() => location.reload(), 1500);
      } else {
        showUserMessage("Algorithm failed. Check console for details.", "error");
      }
    } catch (err) {
      console.error("Error running algorithm:", err);
      showUserMessage("Error running algorithm. Check console.", "error");
    }
  });
} else {
  console.error("runAlgoButton not found in DOM");
}







// Configuration management
async function loadConfigs() {
  if (!SIMULATION_ID) return;
  try {
    const res = await fetch(`/api/list-configs/${SIMULATION_ID}/`);
    const data = await res.json();
    if (!data.success) return;

    const select = document.getElementById("configSelect");
    select.innerHTML = '<option value="">-- select saved config --</option>';
    data.configs.forEach(cfg => {
      const opt = document.createElement("option");
      opt.value = cfg.id;
      opt.textContent = `${cfg.name} (${new Date(cfg.created_at).toLocaleString()})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Error loading configs:", err);
  }
}

// save current simplacement to new saved configuration
document.getElementById("saveConfigButton").addEventListener("click", () => {
  if (!SIMULATION_ID) {
    showUserMessage("No simulation loaded.", "error");
    return;
  }
  showSaveConfigModal();
});

// Handle save config action (called from modal)
window.handleSaveConfig = async (name) => {
  showUserMessage("Saving configuration...", "info");
  try {
    const loadedIds = loadedQueue.map(obj => obj.id);
    const res = await fetch(`/api/save-config/${SIMULATION_ID}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "X-CSRFToken": getCookie("csrftoken"), // uncomment if view is protected
      },
      // body: JSON.stringify({ name })
      // Gather IDs of loaded items
        

        // Send to backend
        body: JSON.stringify({ 
          name, 
          loaded_ids: loadedIds 
        })


    });
    const data = await res.json();
    if (data.success) {
      showUserMessage(data.message || "Configuration saved successfully!", "success");
      await loadConfigs(); // refresh dropdown so new config shows up
    } else {
      showUserMessage("Error saving configuration: " + (data.message || "unknown"), "error");
    }
  } catch (err) {
    console.error("Save config error:", err);
    showUserMessage("Error saving configuration — check console", "error");
  }
};

// load selected configuration (replace simplacements)
document.getElementById("loadConfigButton").addEventListener("click", () => {
  const select = document.getElementById("configSelect");
  const configId = select.value;
  if (!configId) {
    showUserMessage("Please choose a configuration to load.", "error");
    return;
  }

  // Store configId for the modal handler
  window.pendingLoadConfigId = configId;
  showLoadConfigModal();
});

// Handle load config action (called from modal)
window.handleLoadConfig = async () => {
  const configId = window.pendingLoadConfigId;
  showUserMessage("Loading configuration...", "info");

  try {
    const res = await fetch(`/api/load-config/${configId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.success) {
      showUserMessage(data.message || "Configuration loaded successfully!", "success");
      setTimeout(() => location.reload(), 1500); // reload the page so front-end and DB are consistent
    } else {
      showUserMessage("Error loading configuration: " + (data.message || "unknown"), "error");
    }
  } catch (err) {
    console.error("Load config error:", err);
    showUserMessage("Error loading configuration — check console", "error");
  }
};

// run once when page loads to populate list
document.addEventListener("DOMContentLoaded", () => {
  loadConfigs();
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

// let isAnimating = false;
// let isResetMode = false


let loadedQueue = []; // Stack for items that are finished
let rewindItem = null;  // The item currently being animated backward
let animationState = "STOPPED"; // Replaces booleans


// Animation loop
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  // Check if a rewind animation is active
    if (rewindItem) {
        animateRewind();
    } 
    // Check if the forward animation is playing
    else if (animationState === "PLAYING") {
        animateItemsSequentially();
    }
  renderer.render(scene, camera);
  
}

animate();