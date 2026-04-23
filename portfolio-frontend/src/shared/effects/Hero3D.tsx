'use client';

import { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { MeshDistortMaterial, Sphere } from '@react-three/drei';
import { useReducedMotion } from 'framer-motion';

function supportsWebGL(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl2') ||
      canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl');
    return !!gl;
  } catch {
    return false;
  }
}

function Blob() {
  return (
    <Sphere visible args={[1.2, 64, 64]} position={[0, 0, 0]}>
      <MeshDistortMaterial
        color="#3b82f6"
        attach="material"
        distort={0.12}
        speed={0.6}
        roughness={0.4}
        metalness={0.5}
        wireframe
        opacity={0.25}
        transparent
      />
    </Sphere>
  );
}

export default function Hero3D() {
  const reduce = useReducedMotion();
  const [webglOk, setWebglOk] = useState(false);
  const [crashed, setCrashed] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setWebglOk(supportsWebGL()), 0);
    return () => clearTimeout(id);
  }, []);

  if (reduce || !webglOk || crashed) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute top-1/2 right-[-18%] hidden h-[480px] w-[480px] -translate-y-1/2 opacity-20 md:block"
    >
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ failIfMajorPerformanceCaveat: false, powerPreference: 'low-power' }}
        onError={() => setCrashed(true)}
      >
        <ambientLight intensity={0.6} />
        <pointLight position={[5, 5, 5]} intensity={1.2} color="#60a5fa" />
        <Blob />
      </Canvas>
    </div>
  );
}
