#!/usr/bin/env python3
"""AI Team Discussion - 3 pharma AI agents debate clinical development topics."""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-5-20250514"
AGENT_MAX_TOKENS = 1500
SUMMARY_MAX_TOKENS = 2000

AGENTS = {
    "QSP Modeling Scientist": (
        "당신은 QSP(Quantitative Systems Pharmacology) 모델링 전문가입니다. "
        "파킨슨병 치료제 HL192(Nurr1 activator)의 PK/PD 특성, 용량 선정 근거, "
        "전임상-임상 번역(translational) 관점에서 분석합니다. "
        "다른 agent의 의견에 대해 모델링/시뮬레이션 관점에서 구체적으로 반론하거나 지지하세요. "
        "항상 정량적 근거를 제시하려고 노력하세요. 한국어로 답변하세요."
    ),
    "BD & Market Analyst": (
        "당신은 파킨슨병 치료제 시장의 BD(Business Development) 전문가입니다. "
        "경쟁사 파이프라인(BIIB054, prasinezumab, LRRK2 inhibitors 등), "
        "시장 규모, NPV 관점에서 HL192의 포지셔닝을 분석합니다. "
        "다른 agent의 기술적 의견이 상업적 가치에 미치는 영향을 평가하세요. "
        "항상 시장 데이터나 경쟁사 사례를 근거로 제시하세요. 한국어로 답변하세요."
    ),
    "Clinical Development Strategist": (
        "당신은 FDA IND 제출 및 Phase 2 임상시험 기획 전문가입니다. "
        "파킨슨병 치료제 HL192의 임상 개발 전략, 프로토콜 핵심 요소, "
        "규제 당국과의 상호작용 전략, DaTscan 등 영상 엔드포인트 활용을 분석합니다. "
        "다른 agent의 의견이 실제 임상시험 실행 가능성(feasibility)에 미치는 영향을 평가하세요. "
        "항상 규제 가이던스나 선례를 근거로 제시하세요. 한국어로 답변하세요."
    ),
}

DIRECTOR_SYSTEM = (
    "당신은 제약 임상개발 팀의 Director입니다. "
    "3명의 전문가(QSP Modeling Scientist, BD & Market Analyst, Clinical Development Strategist)가 "
    "토론한 내용을 요약합니다. 다음을 포함하세요: "
    "1) 합의 사항 2) 미해결 이견 3) 필요한 의사결정 4) 권고 액션 아이템. "
    "한국어로 답변하세요."
)


def call_agent(client, system_prompt, messages):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=AGENT_MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    )
    return resp.content[0].text


def call_summary(client, messages):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=SUMMARY_MAX_TOKENS,
        system=DIRECTOR_SYSTEM,
        messages=messages,
    )
    return resp.content[0].text


def run_round(client, round_num, topic, history, round_instruction=None):
    """Run one round: each agent responds given topic + history."""
    round_responses = {}
    for name, system_prompt in AGENTS.items():
        msgs = []
        # Initial topic
        msgs.append({"role": "user", "content": f"토론 주제: {topic}"})
        # Replay history
        for entry in history:
            msgs.append({"role": "assistant", "content": entry["text"]})
            msgs.append({"role": "user", "content": "다음 발언자로 넘어갑니다."})

        # Round-specific instruction
        if round_num == 1:
            prompt = "이 주제에 대해 당신의 전문 분야 관점에서 초기 의견을 제시하세요."
        elif round_num == 2:
            prompt = "다른 전문가들의 의견을 검토하고, 반론/보충/질문을 제시하세요."
        elif round_num == 3:
            prompt = "최종 입장을 정리하세요. 합의점과 이견을 명시하세요."
        else:
            prompt = "토론을 계속하세요."

        if round_instruction:
            prompt = f"[Director 지시] {round_instruction}\n\n{prompt}"

        msgs.append({"role": "user", "content": prompt})

        print(f"  [{name}] 응답 생성 중...")
        response = call_agent(client, system_prompt, msgs)
        round_responses[name] = response
        history.append({"agent": name, "round": round_num, "text": response})

    return round_responses


def format_slack_blocks(topic, history, summary):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🧬 AI Team Discussion", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*주제:* {topic}"}},
        {"type": "divider"},
    ]

    current_round = None
    for entry in history:
        if entry["round"] != current_round:
            current_round = entry["round"]
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*--- Round {current_round} ---*"}})
        text = entry["text"]
        if len(text) > 2900:
            text = text[:2900] + "..."
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{entry['agent']}:*\n{text}"}})

    blocks.append({"type": "divider"})
    summary_text = summary if len(summary) <= 2900 else summary[:2900] + "..."
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*📋 Director Summary:*\n{summary_text}"}})

    return blocks


def send_slack(topic, history, summary):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL이 설정되지 않았습니다. Slack 전송을 건너뜁니다.")
        return False

    blocks = format_slack_blocks(topic, history, summary)
    # Slack has a limit of 50 blocks per message; send summary only if too many
    if len(blocks) > 50:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🧬 AI Team Discussion", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*주제:* {topic}"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*📋 Director Summary:*\n{summary[:2900]}"}},
        ]

    resp = requests.post(webhook_url, json={"blocks": blocks})
    if resp.status_code == 200:
        print("Slack 전송 완료!")
        return True
    else:
        print(f"Slack 전송 실패: {resp.status_code} {resp.text}")
        return False


def save_log(topic, history, summary):
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    filename = logs_dir / f"discussion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    lines = [f"# AI Team Discussion\n", f"**날짜:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
             f"**주제:** {topic}\n\n"]

    current_round = None
    for entry in history:
        if entry["round"] != current_round:
            current_round = entry["round"]
            lines.append(f"---\n## Round {current_round}\n\n")
        lines.append(f"### {entry['agent']}\n\n{entry['text']}\n\n")

    lines.append(f"---\n## Director Summary\n\n{summary}\n")

    filename.write_text("".join(lines), encoding="utf-8")
    print(f"로그 저장: {filename}")
    return str(filename)


def run_auto(client, topic):
    print(f"\n=== 토론 주제: {topic} ===\n")
    history = []

    for r in range(1, 4):
        print(f"\n--- Round {r} ---")
        run_round(client, r, topic, history)

    print("\n--- Summary ---")
    summary_msgs = [{"role": "user", "content": f"토론 주제: {topic}\n\n전체 토론 내용:\n\n" +
                     "\n\n".join(f"[Round {e['round']}] {e['agent']}:\n{e['text']}" for e in history) +
                     "\n\n위 토론을 요약해 주세요."}]
    summary = call_summary(client, summary_msgs)
    print(f"\n{summary}")

    log_path = save_log(topic, history, summary)
    send_slack(topic, history, summary)
    return log_path


def run_interactive(client, topic):
    print(f"\n=== 토론 주제: {topic} ===")
    print("명령어: continue(다음 라운드) | end(요약 후 종료) | slack(Slack 전송) | 직접 입력(Director 지시)\n")
    history = []
    round_num = 0
    summary = None

    while True:
        round_num += 1
        print(f"\n--- Round {round_num} ---")
        run_round(client, round_num, topic, history)

        for entry in history:
            if entry["round"] == round_num:
                print(f"\n[{entry['agent']}]:\n{entry['text'][:500]}{'...' if len(entry['text']) > 500 else ''}")

        while True:
            cmd = input("\n입력 (continue/end/slack/직접입력): ").strip()
            if cmd == "continue":
                break
            elif cmd == "end":
                print("\n--- Summary ---")
                summary_msgs = [{"role": "user", "content": f"토론 주제: {topic}\n\n전체 토론 내용:\n\n" +
                                 "\n\n".join(f"[Round {e['round']}] {e['agent']}:\n{e['text']}" for e in history) +
                                 "\n\n위 토론을 요약해 주세요."}]
                summary = call_summary(client, summary_msgs)
                print(f"\n{summary}")
                save_log(topic, history, summary)
                return
            elif cmd == "slack":
                if summary is None:
                    summary_msgs = [{"role": "user", "content": f"토론 주제: {topic}\n\n전체 토론 내용:\n\n" +
                                     "\n\n".join(f"[Round {e['round']}] {e['agent']}:\n{e['text']}" for e in history) +
                                     "\n\n위 토론을 요약해 주세요."}]
                    summary = call_summary(client, summary_msgs)
                send_slack(topic, history, summary)
            elif cmd:
                # Director instruction for next round
                round_num += 1
                print(f"\n--- Round {round_num} (Director 지시) ---")
                run_round(client, round_num, topic, history, round_instruction=cmd)
                for entry in history:
                    if entry["round"] == round_num:
                        print(f"\n[{entry['agent']}]:\n{entry['text'][:500]}{'...' if len(entry['text']) > 500 else ''}")


def main():
    parser = argparse.ArgumentParser(description="AI Team Discussion")
    parser.add_argument("--mode", choices=["auto", "interactive"], default="auto")
    parser.add_argument("--topic", help="토론 주제 (미지정 시 DISCUSSION_TOPIC 환경변수 사용)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 구조만 테스트")
    args = parser.parse_args()

    topic = args.topic or os.environ.get("DISCUSSION_TOPIC", "")
    if not topic:
        print("Error: 토론 주제가 필요합니다. --topic 또는 DISCUSSION_TOPIC 환경변수를 설정하세요.")
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] 주제: {topic}")
        print("[DRY RUN] Agent 3명, Round 3회 실행 예정")
        for name in AGENTS:
            print(f"  - {name}")
        print("[DRY RUN] 완료")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if args.mode == "auto":
        run_auto(client, topic)
    else:
        run_interactive(client, topic)


if __name__ == "__main__":
    main()
