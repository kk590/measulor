import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';

export default function AITailor3D() {
  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const [measurements, setMeasurements] = useState(null);
  const [calibrated, setCalibrated] = useState(false);
  const [username, setUsername] = useState('Guest');
  const [scene, setScene] = useState(null);
  const [bodyModel, setBodyModel] = useState(null);
  const sceneRef = useRef(null);

  // Initialize Three.js Scene
  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const newScene = new THREE.Scene();
    newScene.background = new THREE.Color(0x1a1a2e);

    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(0, 0, 2);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    containerRef.current.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    newScene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 10, 7);
    directionalLight.castShadow = true;
    newScene.add(directionalLight);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      if (bodyModel) {
        bodyModel.rotation.y += 0.003;
      }
      renderer.render(newScene, camera);
    };
    animate();

    sceneRef.current = { scene: newScene, camera, renderer };
    setScene(newScene);

    return () => {
      renderer.dispose();
      if (containerRef.current && renderer.domElement.parentNode === containerRef.current) {
        containerRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Create 3D Body Model
  const create3DBody = (meas) => {
    if (!sceneRef.current) return;
    const { scene: threeScene } = sceneRef.current;

    // Remove old model
    if (bodyModel) {
      threeScene.remove(bodyModel);
    }

    const group = new THREE.Group();

    // Normalize measurements to reasonable scale
    const scale = 0.01; // Convert cm to units
    const shoulder = (meas['Shoulder Width'] || 40) * scale;
    const armLength = (meas['Left Arm Length'] || 55) * scale;
    const torsoLen = (meas['Torso Length'] || 50) * scale;
    const hipWidth = (meas['Hip Width'] || 35) * scale;
    const legLen = (meas['Leg Length'] || 80) * scale;

    // Material
    const skinMat = new THREE.MeshPhongMaterial({ color: 0xffdbac });
    const jointMat = new THREE.MeshPhongMaterial({ color: 0xff6b9d });

    // HEAD
    const headGeom = new THREE.SphereGeometry(shoulder * 0.25, 32, 32);
    const head = new THREE.Mesh(headGeom, skinMat);
    head.position.y = torsoLen + shoulder * 0.15;
    head.castShadow = true;
    group.add(head);

    // TORSO (cylinder)
    const torsoGeom = new THREE.CylinderGeometry(shoulder * 0.35, hipWidth * 0.35, torsoLen, 32);
    const torso = new THREE.Mesh(torsoGeom, skinMat);
    torso.position.y = torsoLen * 0.5;
    torso.castShadow = true;
    group.add(torso);

    // LEFT ARM
    const armGeom = new THREE.CylinderGeometry(shoulder * 0.08, shoulder * 0.07, armLength, 16);
    const leftArm = new THREE.Mesh(armGeom, skinMat);
    leftArm.position.set(-shoulder * 0.4, torsoLen * 0.8, 0);
    leftArm.rotation.z = Math.PI * 0.3;
    leftArm.castShadow = true;
    group.add(leftArm);

    // RIGHT ARM
    const rightArm = new THREE.Mesh(armGeom, skinMat);
    rightArm.position.set(shoulder * 0.4, torsoLen * 0.8, 0);
    rightArm.rotation.z = -Math.PI * 0.3;
    rightArm.castShadow = true;
    group.add(rightArm);

    // LEFT LEG
    const legGeom = new THREE.CylinderGeometry(hipWidth * 0.12, hipWidth * 0.1, legLen, 16);
    const leftLeg = new THREE.Mesh(legGeom, skinMat);
    leftLeg.position.set(-hipWidth * 0.2, -legLen * 0.5, 0);
    leftLeg.castShadow = true;
    group.add(leftLeg);

    // RIGHT LEG
    const rightLeg = new THREE.Mesh(legGeom, skinMat);
    rightLeg.position.set(hipWidth * 0.2, -legLen * 0.5, 0);
    rightLeg.castShadow = true;
    group.add(rightLeg);

    // JOINTS (spheres)
    const jointGeom = new THREE.SphereGeometry(shoulder * 0.05, 16, 16);
    
    const joints = [
      { pos: [-shoulder * 0.4, torsoLen * 0.8, 0] },
      { pos: [shoulder * 0.4, torsoLen * 0.8, 0] },
      { pos: [-hipWidth * 0.2, -legLen * 0.5, 0] },
      { pos: [hipWidth * 0.2, -legLen * 0.5, 0] },
    ];

    joints.forEach(joint => {
      const sphereJoint = new THREE.Mesh(jointGeom, jointMat);
      sphereJoint.position.set(...joint.pos);
      sphereJoint.castShadow = true;
      group.add(sphereJoint);
    });

    threeScene.add(group);
    setBodyModel(group);
  };

  // Camera setup
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ 
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } } 
    })
    .then(stream => {
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    })
    .catch(err => alert('Camera error: ' + err.message));
  }, []);

  const calibrate = async () => {
    setCalibrated(true);
    alert('System calibrated!');
  };

  const measureNow = async () => {
    if (!calibrated) {
      alert('Please calibrate first!');
      return;
    }

    // Mock measurements (in real app, these come from AI)
    const mockMeasurements = {
      'Shoulder Width': 38 + Math.random() * 4,
      'Left Arm Length': 52 + Math.random() * 4,
      'Torso Length': 48 + Math.random() * 4,
      'Inseam': 75 + Math.random() * 5,
      'Hip Width': 35 + Math.random() * 4,
      'Leg Length': 82 + Math.random() * 5,
    };

    setMeasurements(mockMeasurements);
    create3DBody(mockMeasurements);
  };

  const saveMeasurements = () => {
    if (!measurements) {
      alert('No measurements to save!');
      return;
    }
    alert(`Measurements saved for ${username}!`);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0f0f1e', color: '#fff' }}>
      {/* 3D View */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        }}
      />

      {/* Control Panel */}
      <div style={{
        width: '350px',
        padding: '30px',
        overflowY: 'auto',
        background: '#0f0f1e',
        borderLeft: '2px solid #667eea',
      }}>
        <h1 style={{ fontSize: '1.8em', marginBottom: '20px', color: '#667eea' }}>
          👕 AI Tailor 3D
        </h1>

        {/* Video Preview */}
        <div style={{
          marginBottom: '20px',
          borderRadius: '10px',
          overflow: 'hidden',
          border: '2px solid #667eea',
        }}>
          <video
            ref={videoRef}
            style={{ width: '100%', height: 'auto', display: 'block' }}
            autoPlay
            playsInline
          />
        </div>

        {/* Status */}
        <div style={{
          background: '#1a1a2e',
          padding: '15px',
          borderRadius: '8px',
          marginBottom: '20px',
          borderLeft: '4px solid #667eea',
        }}>
          <div style={{ marginBottom: '10px' }}>
            <span style={{ color: '#999' }}>Calibration: </span>
            <span style={{ color: calibrated ? '#48bb78' : '#f56565', fontWeight: 'bold' }}>
              {calibrated ? '✅ Calibrated' : '❌ Not Calibrated'}
            </span>
          </div>
          <div>
            <span style={{ color: '#999' }}>3D Model: </span>
            <span style={{ color: measurements ? '#48bb78' : '#f56565', fontWeight: 'bold' }}>
              {measurements ? '✅ Generated' : '❌ Waiting'}
            </span>
          </div>
        </div>

        {/* Controls */}
        <button
          onClick={calibrate}
          style={{
            width: '100%',
            padding: '12px',
            marginBottom: '10px',
            background: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1em',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'all 0.3s',
          }}
          onMouseOver={(e) => e.target.style.background = '#5568d3'}
          onMouseOut={(e) => e.target.style.background = '#667eea'}
        >
          📏 Calibrate System
        </button>

        <button
          onClick={measureNow}
          style={{
            width: '100%',
            padding: '12px',
            marginBottom: '10px',
            background: '#48bb78',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1em',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'all 0.3s',
          }}
          onMouseOver={(e) => e.target.style.background = '#38a169'}
          onMouseOut={(e) => e.target.style.background = '#48bb78'}
        >
          📊 Generate 3D Model
        </button>

        {/* Measurements */}
        {measurements && (
          <div style={{
            background: '#1a1a2e',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px',
          }}>
            <h3 style={{ marginBottom: '15px', color: '#667eea' }}>📐 Measurements (cm)</h3>
            {Object.entries(measurements).map(([key, value]) => (
              <div key={key} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 0',
                borderBottom: '1px solid #333',
                fontSize: '0.9em',
              }}>
                <span style={{ color: '#999' }}>{key}</span>
                <span style={{ color: '#667eea', fontWeight: 'bold' }}>{value.toFixed(1)} cm</span>
              </div>
            ))}
          </div>
        )}

        {/* User Input & Save */}
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter your name"
          style={{
            width: '100%',
            padding: '10px',
            marginBottom: '10px',
            background: '#1a1a2e',
            border: '2px solid #667eea',
            borderRadius: '8px',
            color: 'white',
            fontSize: '0.9em',
            boxSizing: 'border-box',
          }}
        />

        <button
          onClick={saveMeasurements}
          style={{
            width: '100%',
            padding: '12px',
            background: '#f5576c',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1em',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'all 0.3s',
          }}
          onMouseOver={(e) => e.target.style.background = '#e53e3e'}
          onMouseOut={(e) => e.target.style.background = '#f5576c'}
        >
          💾 Save 3D Model
        </button>

        {/* Info */}
        <div style={{
          marginTop: '20px',
          padding: '15px',
          background: '#1a1a2e',
          borderRadius: '8px',
          fontSize: '0.85em',
          color: '#999',
          lineHeight: '1.6',
        }}>
          <strong style={{ color: '#667eea' }}>💡 How it works:</strong>
          <br />
          1. Click "Calibrate" to start
          <br />
          2. Click "Generate 3D Model" to create your 3D body
          <br />
          3. View your measurements
          <br />
          4. Save your profile
        </div>
      </div>
    </div>
  );
}
