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
    status?: string;
    register_status?: string;
}

interface GlobeViewProps {
    collection?: MyPerfume[];
    isKorean?: boolean;
    onFocusPerfumeChange?: (perfume: MyPerfume | null) => void;
}

const GLOBE_RADIUS = 12;
const DEFAULT_CAMERA_Z = 42;
const CARD_WIDTH = 1.6;
const CARD_HEIGHT = 2.2;
const CARD_THICKNESS = 0.05;

// [TWEAK] Hover/Focus Scale Factors
const HOVER_SCALE = 1.15;
const FOCUS_SCALE = 1.12;
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
    const animationStateRef = useRef<{
        active: boolean;
        startTime: number;
        startPos: THREE.Vector3;
        endPos: THREE.Vector3;
    }>({
        active: false,
        startTime: 0,
        startPos: new THREE.Vector3(),
        endPos: new THREE.Vector3(),
    });
    const lastFocusKeyRef = useRef<string>("");

    useEffect(() => {
        if (!focusedPosition) {
            animationStateRef.current.active = false;
            lastFocusKeyRef.current = "";
            return;
        }

        const nextKey = `${focusedPosition.x.toFixed(3)}|${focusedPosition.y.toFixed(3)}|${focusedPosition.z.toFixed(3)}`;
        if (lastFocusKeyRef.current === nextKey) {
            return;
        }
        lastFocusKeyRef.current = nextKey;

        const from = camera.position.clone();
        const vec = new THREE.Vector3().subVectors(from, focusedPosition);
        const currentDistance = vec.length();
        if (currentDistance <= 0.001) return;

        const desiredDistance = Math.max(14, Math.min(currentDistance * 0.76, 21));
        const dir = vec.normalize();
        const to = focusedPosition.clone().add(dir.multiplyScalar(desiredDistance));

        animationStateRef.current = {
            active: true,
            startTime: performance.now(),
            startPos: from,
            endPos: to,
        };
    }, [focusedPosition, camera]);

    useFrame((state, delta) => {
        if (!controlsRef.current) return;
        const controls = controlsRef.current;

        if (focusedPosition) {
            // 타겟만 지속 추적 (포커스 유지)
            controls.target.lerp(focusedPosition, delta * 6);

            // 카메라는 한 번만 부드럽게 이동하고, 이후에는 사용자 줌/회전 제어권 유지
            if (animationStateRef.current.active) {
                const elapsed = performance.now() - animationStateRef.current.startTime;
                const t = Math.min(1, elapsed / 420);
                const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
                camera.position.lerpVectors(
                    animationStateRef.current.startPos,
                    animationStateRef.current.endPos,
                    eased
                );
                if (t >= 1) {
                    animationStateRef.current.active = false;
                }
            }

        } else {
            // Focus 해제 시: 단순히 Center(0,0,0)을 보게 함
            controls.target.lerp(new THREE.Vector3(0, 0, 0), delta * 2);
            animationStateRef.current.active = false;
            lastFocusKeyRef.current = "";
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
                        <AnimatedCardContent>
                            {/* HTML OVERLAY */}
                            <Html
                                transform
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
                                    opacity: isDimmed ? 0.68 : 1,
                                    filter: isDimmed ? 'saturate(0.78) brightness(0.9)' : 'none',
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
                        </AnimatedCardContent>
                    </group>
                </group>
            </Billboard>
        </Float>
    );
}

// 카드의 내용물을 감싸는 래퍼 (Dim 처리 시 뒤로 물러나는 애니메이션 담당)
function AnimatedCardContent({ children }: { children: React.ReactNode }) {
    const groupRef = useRef<THREE.Group>(null);
    useFrame((state, delta) => {
        if (groupRef.current) {
            // 카드가 과하게 멀어지면 이미지가 사라져 보일 수 있어, z 이동은 비활성화
            const targetZ = 0;
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
export default function ArchiveGlobeView({ collection = [], isKorean = true, onFocusPerfumeChange }: GlobeViewProps) {
    const [focusedId, setFocusedId] = useState<number | null>(null);
    const controlsRef = useRef<any>(null);

    // 컬렉션 데이터가 없을 경우 보여줄 더미 데이터 생성
    const displayConfig = useMemo<MyPerfume[]>(() => {
        if (collection.length > 0) return collection;
        return Array.from({ length: 30 }).map((_, i): MyPerfume => ({
            my_perfume_id: i,
            name: `Perfume No.${i + 1}`,
            name_en: `Perfume No.${i + 1}`,
            name_kr: `센텐스 컬렉션 ${i + 1}`,
            brand: "SCENTENCE",
            brand_kr: "센텐스",
            image_url: null,
            register_status: "HAVE",
            status: "HAVE",
        }));
    }, [collection]);

    // Focus Position Logic
    const focusedPosition = useMemo(() => {
        if (focusedId === null) return null;
        const idx = displayConfig.findIndex(item => item.my_perfume_id === focusedId);
        if (idx === -1) return null;
        return getPositionOnSphere(idx, displayConfig.length, GLOBE_RADIUS);
    }, [focusedId, displayConfig]);

    const focusedPerfume = useMemo(() => {
        if (focusedId === null) return null;
        return displayConfig.find(item => item.my_perfume_id === focusedId) || null;
    }, [focusedId, displayConfig]);

    const focusedImage = useMemo(() => {
        if (!focusedPerfume) return null;
        if (focusedPerfume.image_url) return focusedPerfume.image_url;
        const idx = displayConfig.findIndex(item => item.my_perfume_id === focusedPerfume.my_perfume_id);
        if (idx === -1) return null;
        return MOCK_IMAGES[idx % MOCK_IMAGES.length];
    }, [focusedPerfume, displayConfig]);

    useEffect(() => {
        onFocusPerfumeChange?.(focusedPerfume);
    }, [focusedPerfume, onFocusPerfumeChange]);

    const statusRaw = focusedPerfume?.register_status || focusedPerfume?.status || "HAVE";
    const statusLabel = isKorean
        ? (statusRaw === "HAVE" ? "보유" : statusRaw === "RECOMMENDED" || statusRaw === "WISH" || statusRaw === "WANT" ? "위시" : "기록")
        : (statusRaw === "HAVE" ? "HAVE" : statusRaw === "RECOMMENDED" || statusRaw === "WISH" || statusRaw === "WANT" ? "WISH" : "HAD");
    const statusClass =
        statusRaw === "HAVE"
            ? "bg-indigo-500/20 text-indigo-200 border-indigo-300/40"
            : statusRaw === "RECOMMENDED" || statusRaw === "WISH" || statusRaw === "WANT"
                ? "bg-rose-500/20 text-rose-200 border-rose-300/40"
                : "bg-amber-500/20 text-amber-200 border-amber-300/40";

    const focusedDisplayName = focusedPerfume
        ? (isKorean ? (focusedPerfume.name_kr || focusedPerfume.name) : (focusedPerfume.name_en || focusedPerfume.name))
        : "";
    const focusedDisplayBrand = focusedPerfume
        ? (isKorean ? (focusedPerfume.brand_kr || focusedPerfume.brand) : focusedPerfume.brand)
        : "";

    return (
        <div className="w-full aspect-square rounded-[2rem] overflow-hidden border border-gray-900 shadow-2xl relative bg-black select-none">

            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/30 via-black to-black pointer-events-none" />

            {/* Camera Setup: Far Clip 1000 for visibility */}
            <Canvas shadows camera={{ position: [0, 0, DEFAULT_CAMERA_Z], fov: 38, near: 0.1, far: 1000 }} dpr={[1, 2]}>

                {/* [Visuals: Deep Universe Fog] - 깊이감 생성 */}
                <fog attach="fog" args={['#050505', 20, 100]} />

                {/* [Visuals: Layer 1 - Wide Distant Stars] - 배경에 깔리는 수많은 작은 별들 */}
                <Stars radius={300} depth={100} count={24000} factor={4} saturation={0} fade speed={0} />

                {/* [Visuals: Layer 2 - Bright Nearby Stars] - 반짝이는 큰 별들 */}
                <Stars radius={100} depth={50} count={2200} factor={10} saturation={1} fade speed={0} />

                {/* [Visuals: Foreground Space Dust] - 금빛 우주 먼지 (밀도 증가) */}
                <Sparkles count={180} scale={40} size={2} speed={0} opacity={0.32} color="#ffd700" noise={0} />
                <Sparkles count={120} scale={30} size={1} speed={0} opacity={0.2} color="#ffffff" noise={0} />

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

            {focusedPerfume && (
                <div className="absolute left-1/2 -translate-x-1/2 bottom-4 w-[calc(100%-1.5rem)] max-w-md z-20">
                    <div className="rounded-2xl border border-white/20 bg-black/60 backdrop-blur-xl shadow-[0_18px_42px_rgba(0,0,0,0.58)] px-3.5 py-3">
                        <div className="flex items-center gap-3">
                            <div className="w-14 h-14 rounded-xl bg-white/5 border border-white/10 overflow-hidden shrink-0 flex items-center justify-center">
                                {focusedImage ? (
                                    <img
                                        src={focusedImage}
                                        alt={focusedDisplayName}
                                        className="w-full h-full object-contain"
                                    />
                                ) : (
                                    <span className="text-[10px] text-white/40 font-bold">NO IMG</span>
                                )}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-[10px] uppercase tracking-[0.14em] text-white/65 font-bold truncate">{focusedDisplayBrand}</p>
                                <p className="text-sm sm:text-base text-white font-extrabold leading-tight break-keep">{focusedDisplayName}</p>
                                <span className={`inline-flex mt-1 rounded-full border px-2 py-0.5 text-[10px] font-black tracking-wider ${statusClass}`}>
                                    {statusLabel}
                                </span>
                            </div>
                            <button
                                type="button"
                                onClick={() => setFocusedId(null)}
                                className="shrink-0 w-7 h-7 rounded-full border border-white/25 text-white/80 hover:text-white hover:border-white/40 flex items-center justify-center"
                                aria-label={isKorean ? "포커스 닫기" : "Close focus"}
                            >
                                ×
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
