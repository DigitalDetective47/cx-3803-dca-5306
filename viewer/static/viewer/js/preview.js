import * as THREE from 'three';

console.log("preview.js loaded!");

const container = document.getElementById('preview-container');
const width = container.clientWidth;
const height = container.clientHeight;

// Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xffffff);
const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
camera.position.set(30, 12.5, 20);
camera.lookAt(0, 0, 0);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);


// Preview mesh logic
let previewMesh = null;

export function createPreviewBox(hu) {
    const geometry = new THREE.BoxGeometry(hu.x_size, hu.y_size, hu.z_size);
    const material = new THREE.MeshStandardMaterial({
        color: hu.color || '#9ca3af',
        transparent: true,
        opacity: 0.8
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.scale.set(0.3, 0.3, 0.3);
      const edges = new THREE.EdgesGeometry(geometry);
      const outline = new THREE.LineSegments(
        edges,
        new THREE.LineBasicMaterial({ color: 0x000000 })
      );
    mesh.add(outline);
    return mesh;
}

export function updatePreview(hu) {
    if (previewMesh) {
        scene.remove(previewMesh);
        previewMesh.geometry.dispose();
        previewMesh.material.dispose();
        previewMesh = null;
    }
    if (!hu) {
        return;
    }
    previewMesh = createPreviewBox(hu);
    scene.add(previewMesh);
}

export function removePreview() {
    if (!previewMesh) return;

    scene.remove(previewMesh);

    previewMesh.geometry.dispose();
    previewMesh.material.dispose();

    previewMesh = null;
}

// Animate
function animate() {
    requestAnimationFrame(animate);
    if (previewMesh) {
        previewMesh.rotation.y += 0.02;
        previewMesh.rotation.x += 0.01;
    }
    renderer.render(scene, camera);
}

window.addEventListener('message', (event) => {
    const data = event.data;

    if (data.action === 'remove') {
        removePreview();
        return;
    }

    if (data && data.x_size && data.y_size && data.z_size) {
        updatePreview(data);
    }
});
animate();