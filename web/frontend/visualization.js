import * as THREE from 'https://unpkg.com/three@0.152.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.152.0/examples/jsm/controls/OrbitControls.js';

// -----------------------------------------------------------
// Create sprite with text
// -----------------------------------------------------------
function makeTextSprite(message, parameters = {}) {
    const fontSize = parameters.fontSize || 24;
    const color = parameters.color || '#000000';

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = `${fontSize}px Arial`;
    const textWidth = context.measureText(message).width;
    canvas.width = textWidth + 20;
    canvas.height = fontSize + 10;

    context.font = `${fontSize}px Arial`;
    context.fillStyle = color;
    context.fillText(message, 10, fontSize);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;

    const material = new THREE.SpriteMaterial({map: texture, transparent: true, depthTest: false});
    const sprite = new THREE.Sprite(material);

    sprite.scale.set(canvas.width / 50, canvas.height / 50, 1);
    return sprite;
}

// Helper to generate distinct distinct colors for multiple complexes
function getComplexColor(index) {
    const colors = [
        0x007aff, // iOS Blue
        0x34c759, // iOS Green
        0xaf52de, // Purple
        0xff9500, // Orange
        0x5856d6, // Indigo
        0xff2d55  // Pink
    ];
    return colors[index % colors.length];
}
// -----------------------------------------------------------
// Render ALL geometric complexes in the environment
// -----------------------------------------------------------
function renderEnvironment3D(complexes) {
    const canvas = document.getElementById("visualizationCanvas");

    if (window.THREE_RENDERER) {
        window.THREE_RENDERER.dispose();
    }

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    window.THREE_RENDERER = renderer;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f7); 

    const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.01, 1000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableRotate = false; // Fixed 2D panning/zooming

    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(0, 0, 10);
    scene.add(light);

    // 1. Coordinate Grid
    const gridHelper = new THREE.GridHelper(200, 200, 0x999999, 0xd0d0d0);
    gridHelper.rotation.x = Math.PI / 2; 
    gridHelper.position.z = -0.01; 
    scene.add(gridHelper);

    // 2. Axis Lines
    const axesHelper = new THREE.AxesHelper(100);
    axesHelper.position.z = -0.005; 
    scene.add(axesHelper);

    // 3. Focal Origin Point (0, 0)
    const originGeo = new THREE.SphereGeometry(0.15, 32, 32);
    const originMat = new THREE.MeshBasicMaterial({ trasparent: true, color: 0x333333 });
    const originSphere = new THREE.Mesh(originGeo, originMat);
    originSphere.position.set(0, 0, 0);
    scene.add(originSphere);

    const originLabel = makeTextSprite("(0,0)", { fontSize: 20, color: '#555555' });
    originLabel.position.set(0.4, -0.4, 0);
    scene.add(originLabel);

    // Reset tracking maps
    window.VISUALIZER_MESHES = {}; 

    let minX = 0, maxX = 0, minY = 0, maxY = 0;
    let complexIndex = 0;

    // Loop through every complex in the environment map
    for (const [complexName, complex] of Object.entries(complexes)) {
        const baseColor = getComplexColor(complexIndex);
        complexIndex++;

        const localCoords = {};
        
        // 1. Parse coordinates safely (handles both old array format and new object format)
        for (const [vName, data] of Object.entries(complex.coords)) {
            let x, y, id;

            if (Array.isArray(data)) {
                [x, y] = data;
                id = `fallback_${complexName}_${vName}`;
            } else {
                [x, y] = data.coords;
                id = data.id;
            }

            localCoords[vName] = new THREE.Vector3(x, y, 0);

            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;

            // Render Vertex Sphere
            const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
            // Defaulting vertices to a clean gray color so property tests show up vibrant
            const mat = new THREE.MeshBasicMaterial({ color: 0x8e8e93 }); 
            const sphere = new THREE.Mesh(sphereGeo, mat);
            sphere.position.copy(localCoords[vName]);
            scene.add(sphere);

            // Bind the sphere mesh to the official PolyLogicA Poset ID
            window.VISUALIZER_MESHES[id] = sphere;

            const labelText = `${complexName}:${vName}`;
            const labelSprite = makeTextSprite(labelText, { fontSize: 16, color: '#1c1c1e' });
            labelSprite.position.set(x, y + 0.3, 0); 
            scene.add(labelSprite);
        }

        // Materials setup per complex scope boundaries
        const lineMat = new THREE.LineBasicMaterial({ color: 0x111111, linewidth: 2 });
        const faceMat = new THREE.MeshBasicMaterial({ color: baseColor, transparent: true, opacity: 0.4, side: THREE.DoubleSide });

        // 2. Render Simplices (Edges and Faces)
        if (complex.simplices) {
            for (const simplex of complex.simplices) {
                // Compatibility layer for structured objects vs old raw arrays
                const vertexNames = Array.isArray(simplex) ? simplex : simplex.vertices;
                const pts = vertexNames.map(vName => localCoords[vName]);
                const simplexId = Array.isArray(simplex) ? `fallback_sim_${complexName}` : simplex.id;

                if (pts.length === 3) {
                    // Draw Face Mesh
                    if (!window.VISUALIZER_MESHES[simplexId]) {
                        const geo = new THREE.BufferGeometry().setFromPoints(pts);
                        geo.setIndex([0, 1, 2]);
                        geo.computeVertexNormals();
                        const mesh = new THREE.Mesh(geo, faceMat.clone()); // Cloned to isolate highlights
                        scene.add(mesh);
                        window.VISUALIZER_MESHES[simplexId] = mesh;
                    }

                    // Draw sub-edges if they exist on the structured simplex object
                    if (simplex.edges) {
                        simplex.edges.forEach(edge => {
                            if (!window.VISUALIZER_MESHES[edge.id]) {
                                const edgePts = edge.vertices.map(vName => localCoords[vName]);
                                const edgeGeo = new THREE.BufferGeometry().setFromPoints(edgePts);
                                const line = new THREE.Line(edgeGeo, lineMat.clone());
                                scene.add(line);
                                window.VISUALIZER_MESHES[edge.id] = line;
                            }
                        });
                    }
                } else if (pts.length === 2) {
                    // Draw Standard Line Edge
                    if (!window.VISUALIZER_MESHES[simplexId]) {
                        const geo = new THREE.BufferGeometry().setFromPoints(pts);
                        const line = new THREE.Line(geo, lineMat.clone());
                        scene.add(line);
                        window.VISUALIZER_MESHES[simplexId] = line;
                    }
                }
            }
        }
    }

    // Dynamic zoom calculations
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const width = Math.max(maxX - minX, maxY - minY, 8);
    
    camera.position.set(cx, cy, width * 1.3); 
    camera.lookAt(cx, cy, 0);
    controls.target.set(cx, cy, 0);

    function resizeRenderer() {
        const wrapper = document.getElementById("visWrapper");
        if (!wrapper) return;
        renderer.setSize(wrapper.clientWidth, wrapper.clientHeight, false);
        camera.aspect = wrapper.clientWidth / wrapper.clientHeight;
        camera.updateProjectionMatrix();
    }
    
    resizeRenderer();
    window.addEventListener("resize", resizeRenderer);

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();
}

window.renderEnvironment3D = renderEnvironment3D;

/**
 * Colors the existing Three.js scene elements based on the PolyLogicA output matrix array index matches
 */
window.drawCheckerResult = function(propName, values) {
    if (!window.VISUALIZER_MESHES || Object.keys(window.VISUALIZER_MESHES).length === 0) {
        console.warn("No active tracked elements found to color.");
        return;
    }

    console.log(`Applying logic checker visual highlights for property: ${propName}`);

    // Loop through the boolean evaluation sequence matching PolyLogicA's dimension-sorted indices
    values.forEach((hasProperty, idx) => {
        const id = idx.toString();
        const mesh = window.VISUALIZER_MESHES[id];

        if (mesh && mesh.material) {
            if (hasProperty) {
                mesh.material.color.setHex(0x34c759); // Green
                if (mesh.type === "Mesh") mesh.material.opacity = 0.8;
            } else {
                mesh.material.color.setHex(0xff3b30); // Red
                if (mesh.type === "Mesh") mesh.material.opacity = 0.2;
            }
            mesh.material.needsUpdate = true;
        }
    });
};

window.drawCheckerResult = drawCheckerResult;
