# Pharma AI Team Discussion

AI agent 3명(QSP Modeling Scientist, BD & Market Analyst, Clinical Development Strategist)이 파킨슨병 치료제 HL192 임상개발 주제를 토론하는 자동화 시스템.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env  # API 키 설정
```

## 사용법

```bash
# 자동 모드 (3라운드 → 요약 → Slack 전송)
python ai_team_discussion.py --topic "Phase 2 용량 선정 전략"

# 환경변수로 주제 설정
export DISCUSSION_TOPIC="DaTscan endpoint 리스크"
python ai_team_discussion.py

# 인터랙티브 모드 (라운드마다 개입 가능)
python ai_team_discussion.py --mode interactive --topic "적응증 우선순위"
```

### 인터랙티브 명령어

- `continue` — 다음 라운드 진행
- `end` — 요약 생성 후 종료
- `slack` — 현재까지 결과 Slack 전송
- 직접 입력 — Director 지시로 agent들에게 전달

## 환경변수

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 (필수) |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL (선택) |
| `DISCUSSION_TOPIC` | 토론 주제 (--topic 미지정 시 사용) |

## GitHub Actions

매일 KST 오전 9시에 자동 실행. `topics.txt`에서 순서대로 주제를 선택.

### Secrets 설정

Repository → Settings → Secrets and variables → Actions → New repository secret:
- `ANTHROPIC_API_KEY`: Anthropic API 키
- `SLACK_WEBHOOK_URL`: Slack Webhook URL
