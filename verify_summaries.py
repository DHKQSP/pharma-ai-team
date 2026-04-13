#!/usr/bin/env python3
"""
YouTube 자막 추출 → 요약문 정합성 검증 스크립트
로컬 PC에서 실행하세요 (YouTube 접속 가능한 환경 필요).

사용법:
  pip install youtube-transcript-api anthropic
  export ANTHROPIC_API_KEY="your-key"
  python verify_summaries.py
"""

import os
import sys
import json
from youtube_transcript_api import YouTubeTranscriptApi

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

VIDEOS = [
    {
        "id": "37ZgAbOvDdk",
        "url": "https://youtu.be/37ZgAbOvDdk",
        "title": "Mencacci - 콜린 알포세레이트 MCI 임상 효과 (SIP 2024)",
        "summary": """2024년 이탈리아 정신의학회(SIP)에서 발표된 강연. 클라우디오 멘카치(Claudio Mencacci) 교수가 '경도 인지 장애(MCI) 환자에게 콜린 알포세레이트를 투여했을 때의 임상적 효과'를 주제로 강연.
- 도네페질 병용 요법의 장기 임상적 유의성: 200명 대상 장기 추적 연구. MMSE 및 ADAS-cog 점수 개선. 2~3년 경과 시 더 뚜렷 [02:39]
- 무기력증(Apathy) 관리의 중요성: 치매 전환 위험 2배, 진행 속도 빠름 [06:40]. 항우울제 + 콜린 알포세레이트 병용 시 무기력증 감소
- P300 잠복기 단축: 한국 임상연구, 12주 투여 후 P300 latency 개선 [07:45]
- 3개월 단위 투여 사이클 권장, 휴지기에도 약효 유지 [10:48]. 아침 복용 권고 [11:20]"""
    },
    {
        "id": "bsWrVXm0ifM",
        "url": "https://youtu.be/bsWrVXm0ifM",
        "title": "Biggio - 콜린 알포세레이트 작용기전 약동학 (SIP 2024)",
        "summary": """2024년 이탈리아 정신의학회(SIP)에서 Biggio 교수 강연. 콜린 알포세레이트의 작용 기전과 약동학.
- 의사 처방 필요한 의약품 [00:31]. 아세틸콜린 직접 전구체. 콜린 함량 41% vs 시티콜린 18% [03:39]
- 말초 신경 및 근육 기능 보조: 신경근 접합부 콜린성 전달 강화, 근력 약화 개선 [05:48]
- 수면과 기억력: REM 수면에서 아세틸콜린 핵심 역할 [08:24]
- 뇌 세포막 보호: 전두엽 피질 수축, 시냅스 감소 [10:48]. 인지질 공급으로 세포막 보호 [17:43]"""
    },
    {
        "id": "gM2dtIMSawM",
        "url": "https://youtu.be/gM2dtIMSawM",
        "title": "Biggio - 콜린 알포세레이트 신경약리학적 기전",
        "summary": """Biggio 교수 강연. 콜린 알포세레이트의 신경약리학적 작용 기전.
- 다중 작용 기전: 아세틸콜린 전구체 + 인지질 합성 촉진 + 베타인(메틸기 공여자)으로 대사 [03:31]
- 세포막 안정화: 노화 시 인지질 변형 → 수용체 기능 저하, 시냅스 수축 [21:46]. 세포막 안정화로 유전체까지 신호 전달 [19:08]
- REM 수면과 아세틸콜린: REM에서 아세틸콜린이 뇌 활성화 [12:39]
- 시티콜린 대비 차별점: 직접적 구조, BBB 통과 후 즉시 콜린 해리 [09:08]. 콜린 함량 41% vs 18% [08:03]"""
    },
    {
        "id": "OdoJKxcFwwI",
        "url": "https://www.youtube.com/watch?v=OdoJKxcFwwI",
        "title": "Mencacci - 콜린 알포세레이트 노년기 우울증/무기력증 (SINPF)",
        "summary": """SINPF에서 Mencacci 교수 발표. MCI 환자를 위한 콜린 알포세레이트 임상적 활용.
1. 고령화와 인지 장애: 2050년 치매 환자 급증 전망 [00:28]. 무증상 기간 약 20년 [03:51]
2. 임상적 효능: 3개월 복용 후 중단해도 3개월간 효과 유지 [06:05]. 도네페질 병용 시 퇴화 효과적 억제 [08:18]
3. 무기력증 위험: 가장 치명적 증상 [12:04]. 치매 전환 속도 빠르고 사망 위험 2배 [13:07]. P300 잠복기 단축 확인 [16:03]
4. 처방 가이드: 3개월 투여 사이클 [18:44]. 아침/이른 오후 복용 [19:08]. 부작용 극히 낮음 [19:29]"""
    },
    {
        "id": "c08ceLQi-OA",
        "url": "https://youtu.be/c08ceLQi-OA",
        "title": "손제용 - 콜린 알포세레이트 급여 축소 및 복용 권고",
        "summary": """손제용 원장. 콜린 알포세레이트 급여 기준 축소에 따른 약값 변동 및 처방 권고.
- 급여 기준 변경: MCI 환자 선별 급여 전환, 본인 부담 30%→80% [00:24]
- 비용: 월 약 9,000원→24,000원 [02:08]
- 임상적 유효성: 2023년 연구, 단독 및 도네페질 병용 시 인지 기능 향상 [01:05]
- 대체재 비교: 포스파티딜세린 월 3만원+, 징코 빌로바 월 18,000원. 콜린 알포세레이트 월 24,000원이 비용효과적 [02:36]
- 약물 치료 중단하지 말고 유지 권고 [03:20]"""
    },
]

VERIFICATION_PROMPT = """당신은 의학/약학 콘텐츠 검증 전문가입니다.

아래에 YouTube 영상의 자막 원문과 사용자가 작성한 요약문이 있습니다.
자막 원문을 기반으로 요약문의 정합성을 검증해 주세요.

## 검증 항목

1. **정확성**: 요약에 사실 오류나 원본과 다른 내용이 있는지
2. **누락**: 영상에서 중요하게 다뤘는데 요약에 빠진 내용이 있는지
3. **과잉해석**: 원본에 없는 내용을 요약에서 추가하거나 과장한 부분이 있는지
4. **타임스탬프 정합성**: 요약에 표기된 [MM:SS]가 실제 자막 타이밍과 대략 일치하는지 (±30초 이내면 OK)

## 등급 기준
- **A**: 정확하고 누락 없음. 타임스탬프 대체로 정확.
- **B**: 소소한 오류나 누락이 있지만 전체 맥락은 정확.
- **C**: 사실 오류, 중요한 누락, 또는 과잉해석이 있어 수정 필요.

## 자막 원문
{transcript}

## 사용자 요약문
{summary}

## 출력 형식
한국어로 답변하세요. 아래 형식을 따르세요:

### 등급: [A/B/C]

### 정확성
- (구체적 평가)

### 누락
- (구체적 평가)

### 과잉해석
- (구체적 평가)

### 타임스탬프 정합성
- [MM:SS] → 실제 자막 위치와 비교 결과

### 수정 필요 사항
- (있을 경우 구체적으로)
"""


def fetch_transcript(video_id):
    """자막 추출. 이탈리아어 > 영어 > 한국어 순으로 시도."""
    ytt_api = YouTubeTranscriptApi()
    for langs in [['it'], ['en'], ['ko'], ['it', 'en', 'ko']]:
        try:
            transcript = ytt_api.fetch(video_id, languages=langs)
            entries = []
            for snippet in transcript.snippets:
                minutes = int(snippet.start // 60)
                seconds = int(snippet.start % 60)
                entries.append(f"[{minutes:02d}:{seconds:02d}] {snippet.text}")
            return "\n".join(entries)
        except Exception:
            continue

    # 자동 생성 자막 시도
    try:
        transcript_list = ytt_api.list(video_id)
        for t in transcript_list:
            transcript = t.fetch()
            entries = []
            for snippet in transcript.snippets:
                minutes = int(snippet.start // 60)
                seconds = int(snippet.start % 60)
                entries.append(f"[{minutes:02d}:{seconds:02d}] {snippet.text}")
            return "\n".join(entries)
    except Exception as e:
        return None


def verify_with_claude(client, transcript_text, summary_text):
    """Claude API로 요약문 검증."""
    resp = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": VERIFICATION_PROMPT.format(
                transcript=transcript_text,
                summary=summary_text
            )
        }]
    )
    return resp.content[0].text


def main():
    print("=" * 60)
    print("YouTube 자막 추출 및 요약문 정합성 검증")
    print("=" * 60)

    # Step 1: 자막 추출
    transcripts = {}
    for v in VIDEOS:
        print(f"\n[{v['id']}] {v['title']}")
        print("  자막 추출 중...")
        text = fetch_transcript(v["id"])
        if text:
            transcripts[v["id"]] = text
            lines = text.count("\n") + 1
            print(f"  ✓ 자막 추출 완료 ({lines} lines)")
            # 자막 파일 저장
            with open(f"subtitles/{v['id']}_transcript.txt", "w", encoding="utf-8") as f:
                f.write(text)
        else:
            print("  ✗ 자막을 찾을 수 없습니다")

    if not transcripts:
        print("\n자막을 하나도 추출하지 못했습니다.")
        sys.exit(1)

    # Step 2: Claude API로 검증 (API 키가 있는 경우)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not HAS_ANTHROPIC or not api_key:
        print("\n" + "=" * 60)
        print("자막 추출 완료. AI 검증을 수행하려면:")
        print("  pip install anthropic")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  python verify_summaries.py")
        print("\n자막 파일은 subtitles/ 폴더에 저장되었습니다.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    for v in VIDEOS:
        if v["id"] not in transcripts:
            continue
        print(f"\n{'=' * 60}")
        print(f"검증 중: {v['title']}")
        print("=" * 60)

        result = verify_with_claude(client, transcripts[v["id"]], v["summary"])
        results.append({"video": v, "result": result})
        print(result)

    # 결과 저장
    with open("verification_report.md", "w", encoding="utf-8") as f:
        f.write("# YouTube 요약문 정합성 검증 보고서\n\n")
        for r in results:
            f.write(f"## {r['video']['title']}\n")
            f.write(f"URL: {r['video']['url']}\n\n")
            f.write(r["result"])
            f.write("\n\n---\n\n")
    print(f"\n보고서 저장: verification_report.md")


if __name__ == "__main__":
    os.makedirs("subtitles", exist_ok=True)
    main()
