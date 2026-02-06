import Link from "next/link";

export default function NMapHeader() {
  return (
    <header className="flex items-center justify-between pb-8 border-b-2 border-[#E6DDCF]">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57]">perfume network</p>
        <h1 className="text-4xl font-semibold mt-2">향수 지도</h1>
        <p className="text-sm text-[#5C5448] mt-3">비슷하면서도 다른, 향수 지도로 새로운 취향을 발견해보세요.</p>
      </div>
      <Link href="/" className="h-10 px-6 flex items-center justify-center rounded-full border border-[#E2D7C5] bg-white text-[13px] font-semibold hover:bg-[#F8F4EC]">
        메인으로
      </Link>
    </header>
  );
}
