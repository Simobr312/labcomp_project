import * as THREE from 'https://unpkg.com/three@0.152.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.152.0/examples/jsm/controls/OrbitControls.js';

// -----------------------------------------------------------
// Helper: Generate all k-combinations of an array
// -----------------------------------------------------------
function getCombinations(arr, k) {
    if (k === 0) return [[]];
    if (arr.length === 0) return [];
    const head = arr[0];
    const tail = arr.slice(1);
    const withHead = getCombinations(tail, k - 1).map(c => [head, ...c]);
    const withoutHead = getCombinations(tail, k);
    return [...withHead, ...withoutHead];
}

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
    
    // UPDATED: Enable 3D Orbiting Rotation
    controls.enableRotate = true; 

    // UPDATED: Angle light directions and add Ambient light for standard 3D illumination
    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(10, 20, 15);
    scene.add(dirLight);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    // Axis Lines (remains useful in 3D space)
    const axesHelper = new THREE.AxesHelper(100);
    axesHelper.position.z = -0.005; 
    scene.add(axesHelper);

    // 3. Focal Origin Point (0, 0, 0)
    const originGeo = new THREE.SphereGeometry(0.15, 32, 32);
    const originMat = new THREE.MeshBasicMaterial({ transparent: true, color: 0x333333 });
    const originSphere = new THREE.Mesh(originGeo, originMat);
    originSphere.position.set(0, 0, 0);
    scene.add(originSphere);

    const originLabel = makeTextSprite("(0,0,0)", { fontSize: 20, color: '#555555' });
    originLabel.position.set(0.4, -0.4, 0.4);
    scene.add(originLabel);

    // Reset tracking maps
    window.VISUALIZER_MESHES = {}; 

    // UPDATED: Added min/max Z tracking for proper 3D bounding boxes
    let minX = 0, maxX = 0, minY = 0, maxY = 0, minZ = 0, maxZ = 0;
    let complexIndex = 0;

    // Loop through every complex in the environment map
    for (const [complexName, complex] of Object.entries(complexes)) {
        const baseColor = getComplexColor(complexIndex);
        complexIndex++;

        const localCoords = {};
        
        // UPDATED: Parse coordinates dynamically to support Z-axis
        for (const [vName, data] of Object.entries(complex.coords)) {
            let x = 0, y = 0, z = 0, id;

            if (Array.isArray(data)) {
                x = data[0] || 0;
                y = data[1] || 0;
                z = data[2] || 0;
                id = `fallback_${complexName}_${vName}`;
            } else {
                const coords = data.coords || [];
                x = coords[0] || 0;
                y = coords[1] || 0;
                z = coords[2] || 0;
                id = data.id;
            }

            localCoords[vName] = new THREE.Vector3(x, y, z);

            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
            if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;

            // Render Vertex Sphere
            const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
            const mat = new THREE.MeshBasicMaterial({ color: 0x8e8e93 }); 
            const sphere = new THREE.Mesh(sphereGeo, mat);
            sphere.position.copy(localCoords[vName]);
            scene.add(sphere);

            // Bind the sphere mesh to the official PolyLogicA Poset ID
            window.VISUALIZER_MESHES[id] = sphere;

            const labelText = `${complexName}:${vName}`;
            const labelSprite = makeTextSprite(labelText, { fontSize: 16, color: '#1c1c1e' });
            labelSprite.position.set(x, y + 0.3, z + 0.1); 
            scene.add(labelSprite);
        }

        // Materials setup per complex scope boundaries
        const lineMat = new THREE.LineBasicMaterial({ color: 0x111111, linewidth: 2 });
        const faceMat = new THREE.MeshBasicMaterial({ color: baseColor, transparent: true, opacity: 0.4, side: THREE.DoubleSide });

        // 2. Render Simplices (Edges and Faces)
        if (complex.simplices) {
            for (const simplex of complex.simplices) {
                const vertexNames = Array.isArray(simplex) ? simplex : simplex.vertices;
                const pts = vertexNames.map(vName => localCoords[vName]);
                const simplexId = Array.isArray(simplex) ? `fallback_sim_${complexName}` : simplex.id;

                // UPDATED: Dynamically handle higher-dimensional solid rendering (like tetrahedrons)
                if (pts.length > 3) {
                    if (!window.VISUALIZER_MESHES[simplexId]) {
                        // Group all sub-triangles of higher dimensional simplices
                        const group = new THREE.Group();
                        const triangles = getCombinations(pts, 3);
                        triangles.forEach(triPts => {
                            const geo = new THREE.BufferGeometry().setFromPoints(triPts);
                            geo.setIndex([0, 1, 2]);
                            geo.computeVertexNormals();
                            const subFace = new THREE.Mesh(geo, faceMat.clone());
                            group.add(subFace);
                        });
                        scene.add(group);
                        window.VISUALIZER_MESHES[simplexId] = group;
                    }
                } else if (pts.length === 3) {
                    // Draw Standard Triangle Face Mesh
                    if (!window.VISUALIZER_MESHES[simplexId]) {
                        const geo = new THREE.BufferGeometry().setFromPoints(pts);
                        geo.setIndex([0, 1, 2]);
                        geo.computeVertexNormals();
                        const mesh = new THREE.Mesh(geo, faceMat.clone()); 
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

    // UPDATED: Ground plane grid helper. Sits flat on the ground plane below the complexes.
    const gridHelper = new THREE.GridHelper(200, 200, 0x999999, 0xd0d0d0);
    gridHelper.position.y = minY - 0.5; 
    scene.add(gridHelper);

    // UPDATED: Dynamic 3D camera calculations
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const cz = (minZ + maxZ) / 2;
    
    const rangeX = maxX - minX;
    const rangeY = maxY - minY;
    const rangeZ = maxZ - minZ;
    const maxRange = Math.max(rangeX, rangeY, rangeZ, 8);
    
    // Angled 3D Isometric Viewport Offset
    camera.position.set(cx + maxRange, cy + maxRange, cz + maxRange * 1.5); 
    camera.lookAt(cx, cy, cz);
    controls.target.set(cx, cy, cz);

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

// -----------------------------------------------------------
// UPDATED: Color checker highlights with recursive support for groups
// -----------------------------------------------------------
window.drawCheckerResult = function(propName, values) {
    if (!window.VISUALIZER_MESHES || Object.keys(window.VISUALIZER_MESHES).length === 0) {
        console.warn("No active tracked elements found to color.");
        return;
    }

    console.log(`Applying logic checker visual highlights for property: ${propName}`);

    // Dynamic recursive color applying (for THREE.Group compatibility)
    function setColor(obj, hex, opacity) {
        if (obj.material) {
            obj.material.color.setHex(hex);
            if (obj.isMesh) obj.material.opacity = opacity;
            obj.material.needsUpdate = true;
        }
        if (obj.children && obj.children.length > 0) {
            obj.children.forEach(child => setColor(child, hex, opacity));
        }
    }

    // Loop through the boolean evaluation sequence matching PolyLogicA's dimension-sorted indices
    values.forEach((hasProperty, idx) => {
        const id = idx.toString();
        const mesh = window.VISUALIZER_MESHES[id];

        if (mesh) {
            if (hasProperty) {
                setColor(mesh, 0x34c759, 0.8); // Green (True)
            } else {
                setColor(mesh, 0xff3b30, 0.2); // Red (False)
            }
        }
    });
};

window.drawCheckerResult = drawCheckerResult;