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

// -----------------------------------------------------------
// Render ALL geometric complexes in the environment
// -----------------------------------------------------------
function renderEnvironment3D(complexes) {
    const canvas = document.getElementById("visualizationCanvas");

    if (window.THREE_RENDERER) {
        window.THREE_RENDERER.dispose();
    }

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(devicePixelRatio);
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    window.THREE_RENDERER = renderer;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f7); // Clean, neutral light background

    const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.01, 1000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableRotate = false; // Keep fixed to strict 2D panning/zooming

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
    const originMat = new THREE.MeshBasicMaterial({ color: 0x333333 });
    const originSphere = new THREE.Mesh(originGeo, originMat);
    originSphere.position.set(0, 0, 0);
    scene.add(originSphere);

    const originLabel = makeTextSprite("(0,0)", { fontSize: 20, color: '#555555' });
    originLabel.position.set(0.4, -0.4, 0);
    scene.add(originLabel);

    // -----------------------------------------------------------
    // Parse incoming data from the entire environment
    // -----------------------------------------------------------
    const globalCoords = {};
    const globalSimplices = [];

    // Aggregate all points and simplices from every complex in the environment
    for (const complex of Object.values(complexes)) {
        // Collect coordinates (avoids drawing duplicates if names match)
        for (const [vName, pt] of Object.entries(complex.coords)) {
            globalCoords[vName] = pt;
        }
        // Collect all simplices
        if (complex.simplices) {
            globalSimplices.push(...complex.simplices);
        }
    }

    let minX = 0, maxX = 0, minY = 0, maxY = 0;

    // Materials
    const lineMat = new THREE.LineBasicMaterial({ color: 0x111111, linewidth: 2 });
    const faceMat = new THREE.MeshBasicMaterial({ color: 0x007aff, transparent: true, opacity: 0.4, side: THREE.DoubleSide });

    // Draw Simplices
    for (const simplex of globalSimplices) {
        // Map vertex names to their global coordinates
        const pts = simplex.map(vName => {
            const [x, y] = globalCoords[vName];
            
            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
            
            return new THREE.Vector3(x, y, 0);
        });

        if (pts.length === 2) {
            // Draw 1-Simplex (Edge)
            const geo = new THREE.BufferGeometry().setFromPoints(pts);
            scene.add(new THREE.Line(geo, lineMat));
        } else if (pts.length === 3) {
            // Draw 2-Simplex (Face)
            const geo = new THREE.BufferGeometry().setFromPoints(pts);
            geo.setIndex([0, 1, 2]);
            geo.computeVertexNormals();
            scene.add(new THREE.Mesh(geo, faceMat));
        }
    }

    // Draw 0-Simplices (Vertices) & Labels
    for (const [vName, [x, y]] of Object.entries(globalCoords)) {
        const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
        const mat = new THREE.MeshBasicMaterial({ color: 0xff3b30 }); 
        const sphere = new THREE.Mesh(sphereGeo, mat);
        sphere.position.set(x, y, 0);
        scene.add(sphere);

        const labelText = `${vName} (${x.toFixed(1)}, ${y.toFixed(1)})`;
        const labelSprite = makeTextSprite(labelText, { fontSize: 18, color: '#1c1c1e' });
        labelSprite.position.set(x, y + 0.3, 0); 
        scene.add(labelSprite);
    }

    // Center camera on a bounding area encompassing the global geometry
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const width = Math.max(maxX - minX, maxY - minY, 8);
    
    camera.position.set(cx, cy, width * 1.3); 
    camera.lookAt(cx, cy, 0);
    controls.target.set(cx, cy, 0);

    function resizeRenderer() {
        const wrapper = document.getElementById("visWrapper");
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