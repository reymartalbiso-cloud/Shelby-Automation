"""
utils/mock_fixtures.py
----------------------
Hand-tuned Shelby-voice sample content used when MOCK_CLAUDE=true
in config.json. Lets the entire pipeline be tested end-to-end without
spending a cent on the Anthropic API.

The fixtures match the tone/personality defined in shelby_prompt.py:
- Warm, conversational, encouraging
- 1–2 emojis, no hashtags
- Under 200 words for posts, under 80 words for replies
"""

# ── Daily Post Fixtures (one per day of week) ────────────────
# Keys MUST match Python's datetime.strftime('%A') output exactly.

DAILY_POST_FIXTURES = {
    "Monday": (
        "New week, new chance to make your classroom feel like the magical place it really is 💛\n\n"
        "Monday mornings are when the Class Economy energy is most contagious. "
        "Kids walk in still half-asleep and BAM — they remember they have rent to pay, "
        "a job to clock in for, and a reward they've been saving up for all week.\n\n"
        "Quick reset for today: walk in and announce one new reward on the menu. "
        "Just one. Watch their eyes light up. Watch the engagement shift in 30 seconds.\n\n"
        "What's ONE thing you're excited to try this week? Drop it in the comments — "
        "I want to cheer you on."
    ),

    "Tuesday": (
        "Tuesday tip that changed everything for me 🍎\n\n"
        "Stop chasing students to pay their fines. Seriously. Put a \"Past Due\" "
        "clipboard by the door and let THEM check it on the way out.\n\n"
        "Two things happen:\n"
        "1. They take ownership — it's not you nagging, it's their responsibility\n"
        "2. Peer pressure does the work for you (you'll hear \"dude you owe $3\" "
        "from across the room and you'll smile)\n\n"
        "This took me three years to figure out and I'm handing it to you in a "
        "Tuesday post. You're welcome. Try it this week and tell me what happens."
    ),

    "Wednesday": (
        "Okay this one made me tear up a little 💛\n\n"
        "A teacher in our community shared that her student — the one who NEVER "
        "did homework — saved up his classroom money for four weeks to buy "
        "\"lunch with the teacher.\" Four weeks. Of doing homework. Just to sit "
        "and eat with her.\n\n"
        "That's the whole thing right there. That's why we do Class Economy. "
        "Not for the money. For the moment when a kid decides YOU are worth "
        "saving up for.\n\n"
        "Share a win from your classroom this week, big or small. I want to "
        "hear it. They're never \"too small.\""
    ),

    "Thursday": (
        "Real talk question for you ✨\n\n"
        "How are you handling kids who blow through their money in one day and "
        "then have nothing left for two weeks?\n\n"
        "I've seen teachers do payday loans (with interest!), savings accounts "
        "with bonus interest, even a \"financial advisor\" student job. I'm "
        "curious what's working in YOUR room.\n\n"
        "Drop your strategy below — even if you think it's nothing special. "
        "Someone reading this is about to steal your idea and it's going to "
        "save their year."
    ),

    "Friday": (
        "WE MADE IT 🙌\n\n"
        "Whatever kind of week it was — the great one, the rough one, the "
        "one where you questioned every choice you've ever made — you showed "
        "up. That counts.\n\n"
        "Weekend prep gift: I'm dropping the \"Monday Money Reset\" printable "
        "in the resources tab. Print it Sunday night, hand it out Monday "
        "morning, watch your week start on rails.\n\n"
        "Now close the laptop. Eat something good. The classroom will be "
        "there Monday and so will we."
    ),

    "Saturday": (
        "Saturday confession 🏫\n\n"
        "I just spent 45 minutes laminating reward menu cards while watching "
        "a cooking show. Tell me I'm not the only one who finds this weirdly "
        "therapeutic.\n\n"
        "Teaching brain never fully shuts off and that's okay — as long as "
        "we're laminating, we're not grading, right?\n\n"
        "What's your weirdly satisfying teacher-brain Saturday activity? "
        "I need to know I'm not alone over here."
    ),

    "Sunday": (
        "Sunday setup, the easy version ✨\n\n"
        "If Monday feels heavy already, here's the ONLY Class Economy thing "
        "you need to do tonight:\n\n"
        "Check your reward menu. Are there any items that haven't been "
        "\"bought\" in two weeks? Swap them out. Add ONE new thing. That's it.\n\n"
        "Novelty is the secret sauce. A fresh menu Monday morning is worth "
        "more than any pep talk I could give you. Your future Monday-morning "
        "self is going to thank you."
    ),
}


# ── Weekly Events Fixture ────────────────────────────────────
# Returned as a JSON-in-markdown-code-fence string on purpose — this is the
# real-world shape Claude often returns, and lets us test the strip_code_fences
# parser in weekly_events.py.

WEEKLY_EVENTS_FIXTURE = """```json
[
  {
    "title": "Monday Money Reset Challenge",
    "description": "Post a photo of your fresh reward menu before students walk in Monday. We'll celebrate every single one — the more creative the better. Bonus points if you snuck in a brand new reward.",
    "day_of_week": "Monday",
    "event_type": "challenge"
  },
  {
    "title": "Tuesday Tip Swap Live",
    "description": "Drop your best Class Economy tip in the comments and steal three from someone else. The compounding effect of teachers sharing what works is real magic. Come ready to learn.",
    "day_of_week": "Tuesday",
    "event_type": "share-your-win"
  },
  {
    "title": "Midweek Q&A With Shelby",
    "description": "Bring your messiest Class Economy problem. Whether it's a kid hoarding cash or a fines system that fell apart in week 3 — we troubleshoot it together. No judgement, all solutions.",
    "day_of_week": "Wednesday",
    "event_type": "Q&A"
  },
  {
    "title": "Friday Wins Wall",
    "description": "End the week loud. Share ONE moment from your classroom this week — a student win, a system win, a moment that made you laugh. Let's flood the feed with the good stuff.",
    "day_of_week": "Friday",
    "event_type": "share-your-win"
  }
]
```"""


# ── Comment Reply Fixtures ───────────────────────────────────
# Rotated through in order when comment_reply.py asks for a reply in mock mode.
# Each one matches a different scenario (excited, struggling, question, etc.)

COMMENT_REPLY_FIXTURES = [
    "Oh I LOVE this — you're going to see such a shift this week 💛 Keep me posted on how the kids react. The first time they get to spend their money is everything.",
    "Hang in there, friend. Week 3 is the messy middle for literally every teacher I know. You're not doing it wrong, you're doing it real. DM me if you want to talk it through.",
    "Great instinct! Try setting the rent at about 10% of what they earn in a normal week — high enough they have to plan, low enough nobody feels crushed. You'll dial it in by week two.",
    "Yes yes YES. This is the exact win I needed to read today 🙌 Print this comment out and tape it to your desk. You did that.",
    "Totally fair frustration. The fines piece is the hardest part for everyone — including me. Start with ONE behavior you fine for this week. Just one. Build from there.",
]


# ── Mock Skool Posts (for comment_reply.py to iterate over) ──
# Shape mirrors what the Apify Skool actor would return for posts:list.

MOCK_SHELBY_USER_ID = "shelby_mock_id_123"

MOCK_POSTS = [
    {
        "id": "post_001",
        "body": "New week, new chance to make your classroom feel magical 💛 What are you excited to try this week?",
        "createdBy": {"id": MOCK_SHELBY_USER_ID, "name": "Shelby Lattimore"},
    },
    {
        "id": "post_002",
        "body": "Tuesday tip: stop chasing fines. Put a \"Past Due\" clipboard by the door.",
        "createdBy": {"id": MOCK_SHELBY_USER_ID, "name": "Shelby Lattimore"},
    },
    {
        "id": "post_003",
        "body": "Share a win from your classroom this week!",
        "createdBy": {"id": MOCK_SHELBY_USER_ID, "name": "Shelby Lattimore"},
    },
]


# ── Mock comments (returned by list_comments() in dry-run) ───
# Designed to exercise the filter logic in comment_reply.py:
#   - comment_a: from teacher, no replies yet → SHOULD be replied to (rotates!)
#   - comment_b: from teacher, Shelby already replied → SHOULD be skipped
#   - comment_c: from Shelby herself → SHOULD be skipped
#   - comment_d: from teacher, empty body → SHOULD be skipped with warning
#
# To give variety across scheduler cycles, comment_a rotates through a pool
# of realistic teacher comments. Each call to list_comments() advances the
# rotation so the user sees different content over time.

COMMENT_POOL = [
    ("Ms. Johnson",   "I'm so excited to try the new reward menu this week! Any tips for getting buy-in fast?"),
    ("Mr. Rodriguez", "How do you handle students who blow through all their money in one day? Mine are wild."),
    ("Ms. Chen",      "Quick question — do you use real bills or just tickets? My budget is tight this year."),
    ("Mr. Williams",  "Week 4 over here and I'm completely overwhelmed. Should I scale back or push through?"),
    ("Ms. Thompson",  "My students keep LOSING their classroom money. Any organization hacks that actually work?"),
    ("Mr. Davis",     "Started yesterday and they are obsessed already. Watching them negotiate is the BEST."),
    ("Ms. Anderson",  "Is there a printable for the reward menu? I tried making one and it looks rough lol"),
    ("Mr. Garcia",    "How do you handle parents asking about the money system? I want to send something home."),
    ("Ms. Martinez",  "What age does this work best for? I teach 2nd grade and wondering if it'll click."),
    ("Mr. Thompson",  "I doubled my engagement in three weeks. THANK YOU. I needed this for my sanity."),
    ("Ms. Wilson",    "Do you charge fines for unfinished work? Feels mean but my class needs structure."),
    ("Mr. Lee",       "My TA loves running the bank — best job assignment I've made all year. Highly recommend."),
]

# Module-level rotation index — advances each call so users see fresh comments.
_comment_rotation = {"index": 0}


def _comments_for_post(post_id: str) -> list[dict]:
    """Returns a fresh list of mock comments scoped to a given post.
    The unanswered comment rotates through COMMENT_POOL each call."""
    i = _comment_rotation["index"]
    _comment_rotation["index"] += 1

    pool_idx = i % len(COMMENT_POOL)
    teacher_name, teacher_msg = COMMENT_POOL[pool_idx]

    # Use a stable user ID per teacher name so the same teacher feels consistent
    teacher_user_id = f"teacher_{teacher_name.lower().replace('. ', '_').replace(' ', '_')}"

    return [
        {
            "id": f"{post_id}_comment_a_{pool_idx}",  # different ID each rotation
            "rootId": post_id,
            "body": teacher_msg,
            "createdBy": {"id": teacher_user_id, "name": teacher_name},
            "replies": [],
        },
        {
            "id": f"{post_id}_comment_b",
            "rootId": post_id,
            "body": "This system saved my year. Thank you Shelby!",
            "createdBy": {"id": "teacher_user_77", "name": "Mr. Patel"},
            "replies": [
                {
                    "id": f"{post_id}_reply_x",
                    "body": "You made my whole day with this 💛",
                    "createdBy": {"id": MOCK_SHELBY_USER_ID, "name": "Shelby Lattimore"},
                }
            ],
        },
        {
            "id": f"{post_id}_comment_c",
            "rootId": post_id,
            "body": "Quick clarification — rent is paid weekly, not daily.",
            "createdBy": {"id": MOCK_SHELBY_USER_ID, "name": "Shelby Lattimore"},
            "replies": [],
        },
        {
            "id": f"{post_id}_comment_d",
            "rootId": post_id,
            "body": "",
            "createdBy": {"id": "teacher_user_99", "name": "Ms. Lee"},
            "replies": [],
        },
    ]


def mock_list_comments(post_id: str) -> list[dict]:
    """
    Returns mock comments for a given post ID.

    Combines:
      - The 4 baseline rotating mock comments (Ms. Johnson, etc.)
      - Any unreplied user-submitted comments from user_comments.json
        (added via the dashboard's /api/add-comment endpoint)
    """
    from utils.user_comments import get_unreplied_for_post
    return _comments_for_post(post_id) + get_unreplied_for_post(post_id)


# ── Reply Fixture Counter ────────────────────────────────────
# Module-level counter so each call to mock_reply() returns a different sample,
# rotating through COMMENT_REPLY_FIXTURES.

_reply_counter = {"index": 0}


def get_next_mock_reply() -> str:
    """Returns the next Shelby-voice reply from COMMENT_REPLY_FIXTURES (round-robin)."""
    i = _reply_counter["index"] % len(COMMENT_REPLY_FIXTURES)
    _reply_counter["index"] += 1
    return COMMENT_REPLY_FIXTURES[i]


# ── User-message detection (which fixture to return) ─────────
# claude_client.generate_content() inspects the user_message to decide which
# fixture to return. We keep that classification logic here so all the mock
# behaviour lives in one place.

def select_mock_response(user_message: str) -> str:
    """
    Given the user_message passed to Claude, return the most appropriate
    mock fixture.

    Detection rules:
        - Contains "event ideas" or "JSON array"  → weekly events fixture
        - Contains "reply as Shelby"              → next round-robin comment reply
        - Contains "daily community post"         → today's daily post fixture
        - Anything else                            → Monday daily post (safe default)
    """
    from datetime import datetime
    import pytz

    msg_lower = user_message.lower()

    if "event ideas" in msg_lower or "json array" in msg_lower:
        return WEEKLY_EVENTS_FIXTURE

    if "reply as shelby" in msg_lower or "warm, helpful reply" in msg_lower:
        return get_next_mock_reply()

    if "daily community post" in msg_lower:
        # Try to detect "Today is <Day>" — fall back to current ET day.
        for day in DAILY_POST_FIXTURES:
            if f"today is {day.lower()}" in msg_lower:
                return DAILY_POST_FIXTURES[day]
        # Fallback: pick today's day in Eastern Time
        eastern = pytz.timezone("America/New_York")
        today = datetime.now(eastern).strftime("%A")
        return DAILY_POST_FIXTURES.get(today, DAILY_POST_FIXTURES["Monday"])

    # Safe default if we ever extend the system with a new prompt shape
    return DAILY_POST_FIXTURES["Monday"]
