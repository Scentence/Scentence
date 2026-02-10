/**
 * 에피소드 상세 페이지
 * 에피소드의 전체 콘텐츠와 관련 정보를 표시
 * 
 * 📝 제목 및 콘텐츠 수정 방법:
 * 1. 에피소드 제목/요약 수정: app/perfume-wiki/_data/perfumeWiki.json 파일에서 해당 에피소드의 title, summary 필드 수정
 * 2. 본문 콘텐츠 수정: perfumeWiki.json 파일에서 해당 에피소드에 content 배열 추가/수정
 *    예시: "content": [{ "subtitle": "섹션 제목", "paragraphs": ["단락1", "단락2"] }]
 * 3. 관련 키워드 수정: perfumeWiki.json 파일에서 해당 에피소드에 tags 배열 추가/수정
 */
import Link from "next/link";
import { notFound } from "next/navigation";
import EpisodeHero from "@/components/perfume-wiki/EpisodeHero";
import EpisodeContentSection from "@/components/perfume-wiki/EpisodeContentSection";
import EpisodeCTA from "@/components/perfume-wiki/EpisodeCTA";
import SeriesRelatedCard from "@/components/perfume-wiki/SeriesRelatedCard";
import TagList from "@/components/perfume-wiki/TagList";
import LikeButton from "@/components/perfume-wiki/LikeButton";
import ShareButton from "@/components/perfume-wiki/ShareButton";
import PageLayout from "@/components/common/PageLayout";
import perfumeWikiData from "../../_data/perfumeWiki.json";
import type { PerfumeWikiData, Series, Episode, ContentSection } from "../../types";

const data = perfumeWikiData as PerfumeWikiData;

type EpisodePageProps = {
  params: Promise<{ seriesId: string; episodeId: string }>;
};

/**
 * 시리즈와 에피소드를 ID로 검색
 * @returns 시리즈, 에피소드, 에피소드 번호를 포함한 객체 또는 null
 */
function findSeriesAndEpisode(
  seriesId: string,
  episodeId: string
): { series: Series; episode: Episode; episodeNumber: number } | null {
  for (const season of data.seasons) {
    for (const series of season.series) {
      if (series.id === seriesId) {
        const episodeIndex = series.episodes.findIndex(
          (ep) => ep.id === episodeId
        );
        if (episodeIndex !== -1) {
          return {
            series,
            episode: series.episodes[episodeIndex],
            episodeNumber: episodeIndex + 1,
          };
        }
      }
    }
  }
  return null;
}

/**
 * 에피소드 콘텐츠가 없을 경우 사용할 기본 콘텐츠
 * 
 * 📝 기본 콘텐츠 수정: 아래 함수의 내용을 수정하거나,
 *    app/perfume-wiki/_data/perfumeWiki.json에서 해당 에피소드에 content 필드 추가
 */
function getDefaultContent(): ContentSection[] {
  return [
    {
      subtitle: "향수의 기본 이해",
      paragraphs: [
        "향수는 시간이 지나면서 향이 변화하는 특성을 가지고 있습니다. 탑 노트, 미들 노트, 베이스 노트로 구성되며, 각 단계마다 다른 향을 경험할 수 있습니다.",
        "향수를 선택할 때는 자신의 피부 타입과 취향을 고려하여 선택하는 것이 중요합니다. 같은 향수라도 사람마다 다르게 표현될 수 있습니다.",
      ],
    },
    {
      subtitle: "향수 사용 팁",
      paragraphs: [
        "향수는 체온이 높은 부위에 뿌리면 더 오래 지속되고 향이 잘 퍼집니다. 손목, 목, 귀 뒤가 대표적인 포인트입니다.",
      ],
    },
  ];
}

export default async function EpisodePage({ params }: EpisodePageProps) {
  const { seriesId, episodeId } = await params;
  const result = findSeriesAndEpisode(seriesId, episodeId);

  if (!result) {
    notFound();
  }

  const { series, episode, episodeNumber } = result;

  // 콘텐츠와 태그 설정 (없을 경우 기본값 사용)
  // 📝 기본 태그 수정: 아래 배열을 수정하거나, perfumeWiki.json에서 해당 에피소드에 tags 배열 추가
  const content = episode.content || getDefaultContent();
  const tags = episode.tags || ["향수입문", "향의변화", "탑노트", "미들노트"];

  return (
    <PageLayout subTitle="Perfume Wiki" disableContentPadding>
      <main className="pt-[80px] pb-32 px-3 sm:px-6 max-w-7xl mx-auto">
        <div className="max-w-4xl mx-auto">
          {/* Hero Section */}
          <div className="mb-16">
            <EpisodeHero
              episode={episode}
              seriesTitle={series.title}
              seriesId={seriesId}
              episodeNumber={episodeNumber}
            />
          </div>

          {/* Like & Share Buttons */}
          <div className="mb-16">
            <div className="flex items-center gap-3 justify-center md:justify-start">
              <LikeButton />
              <ShareButton />
            </div>
          </div>

          {/* Content Section */}
          <div className="mb-20">
            <EpisodeContentSection content={content} />
          </div>

          {/* Divider */}
          <div className="mb-16">
            <div className="h-px bg-gradient-to-r from-transparent via-[#E0E0E0] to-transparent" />
          </div>

          {/* Tags Section */}
          <div className="mb-20">
            <div className="space-y-5">
              <h3 className="text-sm font-bold text-[#555]">관련 키워드</h3>
              <TagList tags={tags} />
            </div>
          </div>

          {/* Series Related Section */}
          <div className="mb-20">
            <SeriesRelatedCard series={series} currentEpisodeId={episode.id} />
          </div>

          {/* CTA Section */}
          <div>
            <EpisodeCTA />
          </div>
        </div>
      </main>
    </PageLayout>
  );
}
