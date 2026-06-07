"use client";

import { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import {
  Float,
  MeshDistortMaterial,
  Environment,
  Lightformer,
} from "@react-three/drei";

function Blob() {
  return (
    <Float speed={1.3} rotationIntensity={0.5} floatIntensity={1.1}>
      <mesh>
        <sphereGeometry args={[1, 192, 192]} />
        <MeshDistortMaterial
          color="#3a63ff"
          metalness={0.82}
          roughness={0.19}
          envMapIntensity={2.2}
          distort={0.34}
          speed={1.5}
        />
      </mesh>
    </Float>
  );
}

/** Real liquid-metal blob: a distorting metallic sphere with studio reflections
 *  built from lightformers (no external HDR, works offline). */
export default function LiquidMetal() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Until the WebGL canvas mounts (and for no-JS), show the CSS approximation.
  if (!mounted) {
    return <div aria-hidden className="liquid-blob is-bluechrome absolute inset-0" />;
  }

  return (
    <Canvas
      className="absolute inset-0"
      camera={{ position: [0, 0, 4.4], fov: 30 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      aria-hidden
    >
      <ambientLight intensity={0.6} />
      <Blob />
      <Environment resolution={256}>
        {/* big blue fill — floods the metal with vivid blue */}
        <Lightformer
          form="rect"
          intensity={1.8}
          position={[0, 0, -6]}
          scale={[16, 16, 1]}
          color="#8fb4ff"
        />
        {/* white key — the glossy highlight */}
        <Lightformer
          form="rect"
          intensity={4}
          position={[3, 3, 3]}
          scale={[6, 6, 1]}
          color="#ffffff"
        />
        <Lightformer
          form="rect"
          intensity={2.6}
          position={[-4, 2, 3]}
          scale={[4, 5, 1]}
          color="#cdddff"
        />
        <Lightformer
          form="circle"
          intensity={3}
          position={[0, -3, 2]}
          scale={[4, 4, 1]}
          color="#2c54f0"
        />
        <Lightformer
          form="ring"
          intensity={2}
          position={[3, -1, -2]}
          scale={[3, 3, 1]}
          color="#5b8cff"
        />
      </Environment>
    </Canvas>
  );
}
