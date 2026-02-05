"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree, extend } from "@react-three/fiber";
import { OrbitControls, Html, useCursor, Sparkles, Stars, Float, Billboard, shaderMaterial } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";

interface MyPerfume {
    my_perfume_id: number;
    name: string;
    name_kr?: string;
    name_en?: string;
    brand: string;
    brand_kr?: string;
    image_url: string | null;
}

interface GlobeViewProps {
    collection?: MyPerfume[];
    isKorean?: boolean;
}

const GLOBE_RADIUS = 12;
const CARD_WIDTH = 1.6;
const CARD_HEIGHT = 2.2;
const CARD_THICKNESS = 0.05;

// [TWEAK] Hover/Focus Scale Factors
const HOVER_SCALE = 1.15;
const FOCUS_SCALE = 1.5;
const IMAGE_HOVER_SCALE = 1.1; // 이미지 호버 스케일

const MOCK_IMAGES = [
    "https://images.unsplash.com/photo-1615634260167-c8cdede054de?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1594035910387-fea477942698?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1523293182086-7651a899d60f?auto=format&fit=crop&w=400&q=80",
];

// [수학 로직] 피보나치 구체(Fibonacci Sphere) 알고리즘
// N개의 아이템을 구체 표면에 거의 균등한 간격으로 배치하기 위해 사용합니다.
// i: 인덱스, N: 전체 개수, radius: 구의 반지름
function getPositionOnSphere(i: number, N: number, radius: number) {
    const phi = Math.acos(1 - (2 * (i + 0.5)) / N);
    const theta = Math.PI * (1 + 5 ** 0.5) * i;
    const x = radius * Math.cos(theta) * Math.sin(phi);
    const y = radius * Math.sin(theta) * Math.sin(phi);
    const z = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
}

// [CAMERA LOGIC] 카메라 포커싱 매니저
// 선택된 카드가 있으면 그 위치로 카메라를 부드럽게 이동(Swoosh)시키고, 
// 선택이 해제되면 다시 중앙을 바라보게 합니다.
function FocusManager({ focusedPosition, controlsRef }: { focusedPosition: THREE.Vector3 | null, controlsRef: any }) {
    const { camera } = useThree();

    useFrame((state, delta) => {
        if (!controlsRef.current) return;
        const controls = controlsRef.current;

        if (focusedPosition) {
            // [SWOOSH] 타겟으로 부드럽게 이동
            // lerp(목표지점, 속도): 현재 위치에서 목표 지점으로 점진적 이동
            controls.target.lerp(focusedPosition, delta * 4); // Target 이동 속도

            // [ZOOM] 카메라가 타겟 '앞'으로 이동하여 클로즈업
            // 카메라 위치 = 타겟 위치 + (타겟 방향 벡터 * 거리 8)
            const direction = new THREE.Vector3().subVectors(camera.position, focusedPosition).normalize();
            const targetCamPos = focusedPosition.clone().add(direction.multiplyScalar(8));

            // Camera 이동 Speed Up (Swoosh 느낌 강화)
            camera.position.lerp(targetCamPos, delta * 4);

        } else {
            // Focus 해제 시: 단순히 Center(0,0,0)을 보게 함
            controls.target.lerp(new THREE.Vector3(0, 0, 0), delta * 2);
            // 카메라는 사용자가 둔 위치 그대로 유지 (Auto-Reset 삭제)
        }
        controls.update();
    });
    return null;
}

// 개별 향수 카드 컴포넌트
function PerfumeCard({
    info,
    position,
    mockImage,
    isKorean,
    focusedId,
    setFocusedId
}: {
    info: MyPerfume;
    position: THREE.Vector3;
    mockImage?: string;
    isKorean: boolean;
    focusedId: number | null;
    setFocusedId: (id: number | null) => void;
}) {
    // [FIX] 히트박스와 비주얼 분리: visualRef는 '보이는 부분'만 제어
    const visualRef = useRef<THREE.Group>(null);
    const [hovered, setHover] = useState(false);

    const isFocused = focusedId === info.my_perfume_id;
    const isDimmed = focusedId !== null && !isFocused;

    useCursor(hovered && !isDimmed);

    // [ANIMATION] 비주얼 그룹 스케일링 (히트박스는 영향받지 않음 -> 떨림 방지)
    useFrame((state, delta) => {
        if (visualRef.current) {
            const targetScale = isFocused ? FOCUS_SCALE : (hovered && !isDimmed ? HOVER_SCALE : 1);
            visualRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 15);
        }
    });

    const handlePointerDown = (e: any) => {
        e.stopPropagation();
        setFocusedId(isFocused ? null : info.my_perfume_id);
    };

    const displayBrand = isKorean ? (info.brand_kr || info.brand) : info.brand;
    const displayName = isKorean ? (info.name_kr || info.name) : (info.name_en || info.name);
    const displayImage = info.image_url || mockImage;

    return (
        <Float
            speed={(hovered || isFocused) ? 0 : 1}
            rotationIntensity={0}
            floatIntensity={0.5}
            floatingRange={isFocused ? [0, 0] : [-0.2, 0.2]}
        >
            <Billboard position={position} follow={true} lockX={false} lockY={false} lockZ={false}>
                <group>
                    {/* [HITBOX] 정적 히트박스 (크기 변함 없음 = 안정적) */}
                    <mesh
                        position={[0, 0, CARD_THICKNESS + 0.2]}
                        onPointerDown={handlePointerDown}
                        onPointerOver={(e) => { e.stopPropagation(); if (!isDimmed) setHover(true); }}
                        onPointerOut={() => setHover(false)}
                    >
                        <planeGeometry args={[CARD_WIDTH, CARD_HEIGHT]} />
                        <meshBasicMaterial transparent opacity={0} depthWrite={false} color="red" />
                    </mesh>

                    {/* [VISUALS] 스케일 애니메이션 적용 대상 */}
                    <group ref={visualRef}>
                        <AnimatedCardContent isDimmed={isDimmed} isFocused={isFocused}>

                            {/* [FIX] GOLD RIM (액자 프레임) 
                                카드보다 약간 크게 뒤에 배치하여 테두리처럼 보이게 함
                            */}
                            <mesh position={[0, 0, -0.01]}>
                                <boxGeometry args={[CARD_WIDTH + 0.12, CARD_HEIGHT + 0.12, CARD_THICKNESS - 0.02]} />
                                <meshStandardMaterial
                                    color="#FFD700"      // 리얼 골드
                                    metalness={0.6}      // 우주에서도 보이게 메탈 조금 낮춤
                                    roughness={0.2}
                                    emissive="#000000"   // 발광 제거
                                    emissiveIntensity={0}
                                />
                            </mesh>

                            {/* MAIN DARK BODY (카드 본체) */}
                            <mesh castShadow receiveShadow position={[0, 0, 0.01]}>
                                <boxGeometry args={[CARD_WIDTH, CARD_HEIGHT, CARD_THICKNESS]} />
                                <meshStandardMaterial
                                    color="#1a1a1a"
                                    roughness={0.7}
                                    metalness={0.1}
                                    transparent={true}
                                    opacity={isDimmed ? 0.2 : 1}
                                />
                            </mesh>

                            {/* IMAGE PANEL */}
                            <mesh position={[0, 0.2, CARD_THICKNESS / 2 + 0.03]}>
                                <planeGeometry args={[CARD_WIDTH - 0.1, CARD_HEIGHT - 0.8]} />
                                <meshBasicMaterial
                                    color="#000"
                                    transparent={true}
                                    opacity={isDimmed ? 0.2 : 1}
                                />
                            </mesh>

                            {/* HTML OVERLAY */}
                            {!isDimmed && (
                                <Html
                                    transform
                                    occlude="blending"
                                    position={[0, 0, CARD_THICKNESS / 2 + 0.04]}
                                    style={{
                                        width: '150px',
                                        height: '210px',
                                        pointerEvents: 'none',
                                        userSelect: 'none',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        transition: 'opacity 0.2s',
                                    }}
                                >
                                    <div className="w-full h-full flex flex-col p-2 font-sans antialiased text-left select-none">
                                        <div className="w-full h-[130px] rounded-sm overflow-hidden mb-3 shadow-inner relative bg-transparent">
                                            {displayImage && (
                                                <img
                                                    src={displayImage}
                                                    alt={displayName}
                                                    className="w-full h-full object-contain transition-transform duration-300 ease-out"
                                                    style={{
                                                        transform: (hovered || isFocused) ? `scale(${IMAGE_HOVER_SCALE})` : 'scale(1)',
                                                        backgroundColor: 'transparent'
                                                    }}
                                                />
                                            )}
                                        </div>
                                        <div className="flex-1 w-full flex flex-col justify-start px-1">
                                            <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest mb-1 truncate block" style={{ color: (hovered || isFocused) ? '#FFD700' : '#9CA3AF' }}>
                                                {displayBrand}
                                            </span>
                                            <span className="text-[11px] text-white font-medium leading-snug line-clamp-2 break-keep block">
                                                {displayName}
                                            </span>
                                        </div>
                                    </div>
                                </Html>
                            )}
                        </AnimatedCardContent>
                    </group>
                </group>
            </Billboard>
        </Float>
    );
}

// 카드의 내용물을 감싸는 래퍼 (Dim 처리 시 뒤로 물러나는 애니메이션 담당)
function AnimatedCardContent({ isDimmed, isFocused, children }: { isDimmed: boolean, isFocused: boolean, children: React.ReactNode }) {
    const groupRef = useRef<THREE.Group>(null);
    useFrame((state, delta) => {
        if (groupRef.current) {
            // Dimmed -> Move Back (z: -15) 화면 뒤로 멀어짐
            const targetZ = isDimmed ? -15 : 0;
            groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, targetZ, delta * 3);
        }
    });
    return <group ref={groupRef}>{children}</group>;
}

// 배경 클릭 시 포커스 해제를 위한 투명 메쉬
function Background({ onReset }: { onReset: () => void }) {
    return (
        <mesh onPointerDown={(e) => { e.stopPropagation(); onReset(); }} position={[0, 0, -30]} scale={[100, 100, 1]}>
            <planeGeometry />
            <meshBasicMaterial visible={false} />
        </mesh>
    );
}

// [MAIN COMPONENT] 3D 갤럭시 뷰 메인
export default function ArchiveGlobeView({ collection = [], isKorean = true }: GlobeViewProps) {
    const [focusedId, setFocusedId] = useState<number | null>(null);
    const controlsRef = useRef<any>(null);

    // 컬렉션 데이터가 없을 경우 보여줄 더미 데이터 생성
    const displayConfig = useMemo(() => {
        if (collection.length > 0) return collection;
        return Array.from({ length: 30 }).map((_, i) => ({
            my_perfume_id: i,
            name: `Perfume No.${i + 1}`,
            name_en: `Perfume No.${i + 1}`,
            name_kr: `센텐스 컬렉션 ${i + 1}`,
            brand: "SCENTENCE",
            brand_kr: "센텐스",
            image_url: null,
        }));
    }, [collection]);

    // Focus Position Logic
    const focusedPosition = useMemo(() => {
        if (focusedId === null) return null;
        const idx = displayConfig.findIndex(item => item.my_perfume_id === focusedId);
        if (idx === -1) return null;
        return getPositionOnSphere(idx, displayConfig.length, GLOBE_RADIUS);
    }, [focusedId, displayConfig]);

    return (
        <div className="w-full h-[700px] rounded-[2rem] overflow-hidden border border-gray-900 shadow-2xl relative bg-black select-none">

            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/30 via-black to-black pointer-events-none" />

            {/* Camera Setup: Far Clip 1000 for visibility */}
            <Canvas shadows camera={{ position: [0, 0, 38], fov: 38, near: 0.1, far: 1000 }} dpr={[1, 2]}>

                {/* [Visuals: Deep Universe Fog] - 깊이감 생성 */}
                <fog attach="fog" args={['#050505', 20, 100]} />

                {/* [Visuals: Layer 1 - Wide Distant Stars] - 배경에 깔리는 수많은 작은 별들 */}
                <Stars radius={300} depth={100} count={50000} factor={4} saturation={0} fade speed={1} />

                {/* [Visuals: Layer 2 - Bright Nearby Stars] - 반짝이는 큰 별들 */}
                <Stars radius={100} depth={50} count={5000} factor={10} saturation={1} fade speed={2} />

                {/* [Visuals: Foreground Space Dust] - 금빛 우주 먼지 (밀도 증가) */}
                <Sparkles count={500} scale={40} size={2} speed={0.4} opacity={0.5} color="#ffd700" noise={1} />
                <Sparkles count={300} scale={30} size={1} speed={0.8} opacity={0.3} color="#ffffff" noise={0.5} />

                <ambientLight intensity={0.5} />
                <spotLight position={[10, 10, 20]} angle={0.5} penumbra={1} intensity={2} color="#ffffff" />

                <Background onReset={() => setFocusedId(null)} />
                <FocusManager focusedPosition={focusedPosition} controlsRef={controlsRef} />

                <group>
                    {displayConfig.map((item, idx) => {
                        const position = getPositionOnSphere(idx, displayConfig.length, GLOBE_RADIUS);
                        const mockImg = MOCK_IMAGES[idx % MOCK_IMAGES.length];

                        return (
                            <PerfumeCard
                                key={item.my_perfume_id}
                                info={item}
                                position={position}
                                mockImage={mockImg}
                                isKorean={isKorean}
                                focusedId={focusedId}
                                setFocusedId={setFocusedId}
                            />
                        );
                    })}
                </group>

                <OrbitControls
                    ref={controlsRef}
                    enableRotate={true}
                    enablePan={false}
                    enableZoom={true}
                    minDistance={2}
                    maxDistance={100}
                    autoRotate={!focusedId}
                    autoRotateSpeed={0.05}
                    dampingFactor={0.05}
                />

                {/* Bloom Effect 제거: 눈부심(눈공격) 원천 차단 */}
            </Canvas>

            <div className="absolute bottom-6 left-0 w-full text-center pointer-events-none opacity-30 select-none">
                <span className="text-[10px] text-white tracking-[0.2em] font-light font-sans">
                    CLICK TO FOCUS • SCROLL TO ZOOM
                </span>
            </div>
        </div>
    );
}