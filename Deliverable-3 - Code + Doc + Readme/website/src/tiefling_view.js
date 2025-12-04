import * as THREE from './three.module.js';

/**
 * TieflingView - renders a single 3D view of an image and a depth map in a canvas.
 * Implements "Depth Discontinuity Meshing" (Mesh Tearing) to handle occlusion.
 */
export const TieflingView = function (container, image, depthMap, options) {

    let mouseXOffset = options.mouseXOffset ?? 0;

    let focus = options.focus ?? 0.5;
    let baseMouseSensitivity = options.baseMouseSensitivity || 0.5;
    let mouseSensitivityX = baseMouseSensitivity;
    let mouseSensitivityY = baseMouseSensitivity;
    let devicePixelRatio = options.devicePixelRatio || Math.min(window.devicePixelRatio, 2) || 1;
    let meshResolution = options.meshResolution || 1024;
    let meshDepth = options.meshDepth || 1;
    let expandDepthmapRadius = options.expandDepthmapRadius ?? 0;
    let cropPercent = options.cropPercent ?? 0;

    let containerWidth = container.offsetWidth;
    let containerHeight = container.offsetHeight;

    let camera, renderer, mesh, bgMesh;
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let imageAspectRatio;

    let scene;
    let scissorX = 0, scissorY = 0, scissorWidth = containerWidth, scissorHeight = containerHeight;

    const easing = 0.05;
    let animationFrameId;

    let material;
    let uniforms = {
        map: { value: null },
        mouseDelta: { value: new THREE.Vector2(0, 0) },
        focus: { value: focus },
        meshDepth: { value: meshDepth },
        sensitivity: { value: baseMouseSensitivity },
        layerSensitivity: { value: options.foregroundSensitivity ?? 0.05 },  // Foreground: minimal movement
        groundedMode: { value: options.groundedMode ?? true }  // Enable grounded parallax by default
    };

    // Separate uniforms for background to allow different texture and sensitivity
    let bgUniforms = {
        map: { value: null },
        mouseDelta: uniforms.mouseDelta, // Share mouse delta
        focus: uniforms.focus,           // Share focus
        meshDepth: uniforms.meshDepth,   // Share depth scale
        sensitivity: uniforms.sensitivity, // Share base sensitivity
        layerSensitivity: { value: options.backgroundSensitivity ?? 1.0 }  // Background: full parallax
    };

    init();
    animate();

    function init() {
        scene = new THREE.Scene();
        scene.background = null;

        const fov = 45;
        camera = new THREE.PerspectiveCamera(fov, containerWidth / containerHeight, 0.1, 1000);
        camera.position.z = 4;
        camera.lookAt(0, 0, 0);

        renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true });
        renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
        renderer.setPixelRatio(devicePixelRatio);
        renderer.setSize(containerWidth, containerHeight);

        updateScissorDimensions();

        container.appendChild(renderer.domElement);

        const textureLoader = new THREE.TextureLoader();

        // Load Main Image (Foreground Mesh)
        const imagePromise = new Promise(resolve => {
            textureLoader.load(image, texture => {
                texture.colorSpace = THREE.LinearSRGBColorSpace;
                texture.minFilter = THREE.LinearFilter;
                texture.magFilter = THREE.LinearFilter;
                uniforms.map.value = texture;
                imageAspectRatio = texture.image.width / texture.image.height;
                resolve();
            });
        });

        // Load Background Image
        let bgImagePromise = Promise.resolve();
        if (options.background) {
            bgImagePromise = new Promise(resolve => {
                textureLoader.load(options.background, texture => {
                    texture.colorSpace = THREE.LinearSRGBColorSpace;
                    texture.minFilter = THREE.LinearFilter;
                    texture.magFilter = THREE.LinearFilter;
                    bgUniforms.map.value = texture;
                    resolve();
                });
            });
        }

        // Load Mask
        let maskPromise = Promise.resolve(null);
        if (options.mask) {
            maskPromise = new Promise(resolve => {
                const img = new Image();
                img.src = options.mask;
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    const maskData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    resolve(maskData);
                };
            });
        }

        // Load Foreground Depth
        const depthPromise = new Promise(resolve => {
            const img = new Image();
            img.src = depthMap;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                let depthData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                resolve(depthData);
            };
        });

        // Load Background Depth (if available)
        let bgDepthPromise = Promise.resolve(null);
        if (options.backgroundDepthMap) {
            bgDepthPromise = new Promise(resolve => {
                const img = new Image();
                img.src = options.backgroundDepthMap;
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    let depthData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    resolve(depthData);
                };
            });
        }

        Promise.all([imagePromise, bgImagePromise, depthPromise, maskPromise, bgDepthPromise]).then((results) => {
            const depthData = results[2];
            const maskData = results[3];
            const bgDepthData = results[4];

            // 1. Create Foreground Mesh (Torn)
            const geometry = createTornGeometry(
                Math.min(meshResolution, depthData.width),
                Math.min(meshResolution, depthData.height),
                depthData,
                maskData,
                true // Enable tearing
            );

            material = new THREE.ShaderMaterial({
                vertexShader: getVertexShader(),
                fragmentShader: getFragmentShader(),
                uniforms: uniforms,
                side: THREE.DoubleSide,
                transparent: true,  // Enable transparency for foreground
                depthWrite: true
            });

            mesh = new THREE.Mesh(geometry, material);
            scene.add(mesh);

            // 2. Create Background Mesh (Solid, Displaced)
            if (bgUniforms.map.value) {
                let bgGeo;
                if (bgDepthData) {
                    // Use background depth map for displacement
                    bgGeo = createTornGeometry(
                        Math.min(meshResolution, bgDepthData.width),
                        Math.min(meshResolution, bgDepthData.height),
                        bgDepthData,
                        null, // No mask for background
                        false // No tearing for background
                    );
                } else {
                    // Fallback to flat plane if no depth map
                    // But we want it to be compatible with the shader which expects 'depth' attribute
                    // So we create a geometry with 0 depth
                    bgGeo = createTornGeometry(
                        100, 100, // Low res
                        { width: 100, height: 100, data: new Uint8Array(100 * 100 * 4).fill(0) }, // Zero depth
                        null,
                        false
                    );
                }

                const bgMaterial = new THREE.ShaderMaterial({
                    vertexShader: getVertexShader(),
                    fragmentShader: getFragmentShader(),
                    uniforms: bgUniforms,
                    side: THREE.DoubleSide
                });

                bgMesh = new THREE.Mesh(bgGeo, bgMaterial);
                // Place slightly behind to avoid Z-fighting, but depth displacement will handle the rest
                bgMesh.position.z = -0.05;
                scene.add(bgMesh);
            }

            onResize();
        });
    }

    function getVertexShader() {
        return `
            uniform vec2 mouseDelta;
            uniform float focus;
            uniform float meshDepth;
            uniform float sensitivity;
            uniform float layerSensitivity;
            uniform bool groundedMode;
            
            attribute float depth;
            
            varying vec2 vUv;
            
            void main() {
                vUv = uv;
                vec3 pos = position;
                
                float actualDepth = depth * meshDepth;
                float focusDepth = focus * meshDepth;
                
                // Base parallax displacement
                vec2 baseRotate = mouseDelta * sensitivity * 
                    (1.0 - focus) * 
                    (actualDepth - focusDepth) * 
                    vec2(-1.0, 1.0);
                
                // Apply layer-specific sensitivity
                vec2 rotate = baseRotate * layerSensitivity;
                
                // Grounded mode: Create vertical gradient for foreground
                // Bottom (v=0) moves with background, top (v=1) has minimal movement
                if (groundedMode && layerSensitivity < 0.5) {
                    // This is the foreground layer (low sensitivity)
                    // Gradient from bottom to top: 1.0 (bottom) to layerSensitivity (top)
                    float verticalGradient = mix(1.0, layerSensitivity, vUv.y);
                    rotate = baseRotate * verticalGradient;
                }
            
                // Apply displacement
                pos.xy += rotate;
            
                gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
            }
        `;
    }

    function getFragmentShader() {
        return `
            uniform sampler2D map;
            varying vec2 vUv;

            void main() {
                vec4 texColor = texture2D(map, vUv);
                gl_FragColor = texColor;
            }
        `;
    }

    function createTornGeometry(width, height, depthData, maskData, enableTearing) {
        const imageAspect = depthData.width / depthData.height;
        const geometry = new THREE.BufferGeometry();

        const numPoints = width * height;
        const vertices = new Float32Array(numPoints * 3);
        const uvs = new Float32Array(numPoints * 2);
        const depths = new Float32Array(numPoints);
        const maskValues = new Float32Array(numPoints);

        // 1. Generate Vertices
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const i = y * width + x;

                const u = x / (width - 1);
                const v = 1 - (y / (height - 1));

                // Sample depth
                const pixelX = Math.floor(u * (depthData.width - 1));
                const pixelY = Math.floor((1 - v) * (depthData.height - 1));
                const pixelIdx = (pixelY * depthData.width + pixelX) * 4;

                let d = 0;
                if (pixelIdx < depthData.data.length) {
                    d = depthData.data[pixelIdx] / 255.0;
                }

                // Sample mask
                let m = 0;
                if (maskData) {
                    const maskX = Math.floor(u * (maskData.width - 1));
                    const maskY = Math.floor((1 - v) * (maskData.height - 1));
                    const maskIdx = (maskY * maskData.width + maskX) * 4;
                    if (maskIdx < maskData.data.length) {
                        m = maskData.data[maskIdx] > 128 ? 1.0 : 0.0;
                    }
                }

                // Position
                const vx = (u - 0.5) * imageAspect;
                const vy_pos = (0.5 - (y / (height - 1)));

                // Apply depth to Z
                const z = d * meshDepth;

                // Perspective Correction:
                // When we move vertices closer (z > 0), they appear larger/shifted due to perspective.
                // We scale x/y down to keep them visually in the same place as the original image.
                // Camera is at z=4.
                const cameraZ = 4.0;
                const perspectiveScale = (cameraZ - z) / cameraZ;

                vertices[i * 3] = vx * perspectiveScale;
                vertices[i * 3 + 1] = vy_pos * perspectiveScale;
                vertices[i * 3 + 2] = z;

                uvs[i * 2] = u;
                uvs[i * 2 + 1] = v;

                depths[i] = d;
                maskValues[i] = m;
            }
        }

        // 2. Generate Indices
        const indices = [];
        const thresholdBase = 0.03;

        for (let y = 0; y < height - 1; y++) {
            for (let x = 0; x < width - 1; x++) {
                const a = y * width + x;
                const b = y * width + (x + 1);
                const c = (y + 1) * width + x;
                const d = (y + 1) * width + (x + 1);

                if (!enableTearing) {
                    // Always add triangles for background
                    indices.push(a, c, b);
                    indices.push(b, c, d);
                    continue;
                }

                const da = depths[a];
                const db = depths[b];
                const dc = depths[c];
                const dd = depths[d];

                const ma = maskValues[a];
                const mb = maskValues[b];
                const mc = maskValues[c];
                const md = maskValues[d];

                const minDepth = Math.min(da, db, dc, dd);
                const maxDepth = Math.max(da, db, dc, dd);
                const diff = maxDepth - minDepth;

                const allInMask = (ma + mb + mc + md) === 4.0;
                const allOutMask = (ma + mb + mc + md) === 0.0;

                if (allInMask) {
                    // Fully inside subject -> Keep it solid!
                    indices.push(a, c, b);
                    indices.push(b, c, d);
                } else if (allOutMask) {
                    // Fully outside subject (background) -> Check depth threshold
                    if (diff < thresholdBase) {
                        indices.push(a, c, b);
                        indices.push(b, c, d);
                    }
                } else {
                    // Mixed (Boundary) -> ALWAYS TEAR
                    // This prevents connecting foreground to background (stretching)
                    // The inpainted background mesh will fill this gap.
                }
            }
        }

        geometry.setIndex(indices);
        geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
        geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
        geometry.setAttribute('depth', new THREE.BufferAttribute(depths, 1));

        geometry.computeVertexNormals();

        return geometry;
    }

    function updateScissorDimensions() {
        if (!imageAspectRatio) return;

        const containerAspect = containerWidth / containerHeight;
        if (containerAspect > imageAspectRatio) {
            scissorHeight = containerHeight;
            scissorWidth = containerHeight * imageAspectRatio;
        } else {
            scissorWidth = containerWidth;
            scissorHeight = containerWidth / imageAspectRatio;
        }
        scissorX = (containerWidth - scissorWidth) / 2;
        scissorY = (containerHeight - scissorHeight) / 2;
    }

    function animate() {
        animationFrameId = requestAnimationFrame(animate);

        const mouseSensitivityFocusFactor = 0.3 + 0.7 * 2 * focus;

        targetX += (mouseSensitivityFocusFactor * mouseX * mouseSensitivityX - targetX) * easing;
        targetY += (mouseSensitivityFocusFactor * mouseY * mouseSensitivityY - targetY) * easing;

        uniforms.mouseDelta.value.set(targetX, -targetY);
        uniforms.focus.value = focus;
        uniforms.sensitivity.value = baseMouseSensitivity;

        if (scissorWidth > 0 && scissorHeight > 0) {
            renderer.setScissorTest(true);
            renderer.setScissor(scissorX, scissorY, scissorWidth, scissorHeight);
            renderer.render(scene, camera);
        }
    }

    function onMouseMove(event, sensitivityMultiplier = 1.0) {
        const rect = container.getBoundingClientRect();
        mouseX = Math.min(1, Math.max(-1, (event.clientX - rect.left) / containerWidth * 2 - 1));
        mouseY = Math.min(1, Math.max(-1, (event.clientY - rect.top) / containerHeight * 2 - 1));

        // Apply sensitivity multiplier (for touch events)
        mouseX *= sensitivityMultiplier;
        mouseY *= sensitivityMultiplier;

        // Clamp again after multiplier
        mouseX = Math.min(1, Math.max(-1, mouseX));
        mouseY = Math.min(1, Math.max(-1, mouseY));

        mouseX += 2 * mouseXOffset;
        mouseX = -mouseX;
    }

    function updateMouseSensitivity() {
        mouseSensitivityX = baseMouseSensitivity;
        mouseSensitivityY = baseMouseSensitivity;
    }

    const onResize = () => {
        containerWidth = container.offsetWidth;
        containerHeight = container.offsetHeight;

        renderer.setSize(containerWidth, containerHeight);
        camera.aspect = containerWidth / containerHeight;
        camera.updateProjectionMatrix();

        updateScissorDimensions();

        if (mesh) {
            const imageAspect = imageAspectRatio || 1;
            const containerAspect = containerWidth / containerHeight;

            const visibleHeight = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.position.z;
            const visibleWidth = visibleHeight * camera.aspect;

            let scale;
            if (containerAspect > imageAspect) {
                scale = visibleHeight / 1;
            } else {
                scale = visibleWidth / imageAspect;
            }

            // Apply crop/zoom
            const extraZoom = 1.0; // Removed forced 15% zoom
            if (cropPercent > 0) {
                scale *= (1 + cropPercent / 100) * extraZoom;
            } else {
                scale *= extraZoom;
            }

            mesh.scale.set(scale, scale, 1);
            if (bgMesh) {
                // Fix: Do not zoom background by 1.1 (10%). This causes misalignment.
                // Instead, scale it up slightly to compensate for being further back (z = -0.05).
                // This ensures it visually matches the foreground size.
                const bgZ = bgMesh.position.z;
                const cameraZ = camera.position.z;
                const bgScaleCorrection = (cameraZ - bgZ) / cameraZ;

                bgMesh.scale.set(scale * bgScaleCorrection, scale * bgScaleCorrection, 1);
            }
        }

        updateMouseSensitivity();
    };

    window.addEventListener('resize', onResize);
    document.addEventListener('mousemove', onMouseMove);

    document.addEventListener('touchmove', (event) => {
        const touchX = event.touches[0].clientX;
        const touchY = event.touches[0].clientY;
        onMouseMove({ clientX: touchX, clientY: touchY }, 2.5); // 2.5x sensitivity for touch
    });

    return {
        destroy: function () {
            window.removeEventListener('resize', onResize);
            document.removeEventListener('mousemove', onMouseMove);

            if (material && material.map) {
                material.map.dispose();
            }

            if (mesh) {
                mesh.geometry.dispose();
                material.dispose();
            }

            if (bgMesh) {
                bgMesh.geometry.dispose();
                bgMesh.material.dispose();
            }

            if (renderer && renderer.domElement && container.contains(renderer.domElement)) {
                renderer.dispose();
                container.removeChild(renderer.domElement);
            }

            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
        },

        onMouseMove: onMouseMove,

        setFocus: function (value) {
            focus = value;
        },
        setBaseMouseSensitivity: function (value) {
            baseMouseSensitivity = value;
            updateMouseSensitivity();
        },
        setDevicePixelRatio: function (value) {
            devicePixelRatio = value;
            if (renderer) {
                renderer.setPixelRatio(devicePixelRatio);
            }
        },
        setMouseXOffset: function (value) {
            mouseXOffset = value;
        },
        setExpandDepthmapRadius: function (value) {
            expandDepthmapRadius = value;
        },
        setLayerSensitivities: function (foregroundSens, backgroundSens) {
            if (uniforms && uniforms.layerSensitivity) {
                uniforms.layerSensitivity.value = foregroundSens;
            }
            if (bgUniforms && bgUniforms.layerSensitivity) {
                bgUniforms.layerSensitivity.value = backgroundSens;
            }
        },
        setGroundedMode: function (value) {
            if (uniforms && uniforms.groundedMode) {
                uniforms.groundedMode.value = value;
            }
        }
    };
}