#!/usr/bin/env python3
"""Builds channels/cribcommittee/channel.json and episodes 001-030 (The Crib Committee, Google Flow channel).

Babies hold a board meeting about their parents. No names: every clip is a different baby.
Each episode = 8 x 8 s Veo 3.1 Lite clips = 64 s (two free Flow accounts: clips 1-5 + 6-8):
  clip 1  the Chair (tiny tie + reading glasses) opens the meeting and states the agenda
  clip 2-7 six delegates each make one wish / complaint (humour + a real parenting insight)
  clip 8  an eighth delegate closes with the lesson; the swaddled newborn intern delivers the running gag
Every shot carries a ready-to-paste `flow_prompt`. Re-run safely:
  python tools/generators/build_cribcommittee_001-030.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "channels" / "cribcommittee"

STYLE = ("Vertical 9:16, hyper-realistic cinematic photo style, shallow depth of field, soft warm window light, "
         "natural baby skin texture, warm cinematic colour grade")
SET = ("seated at a miniature boardroom table made of wooden building blocks, in a sunlit nursery set up like a "
       "grand executive office, tall window softly blurred behind, no name plates, no signs")
TAIL = "No music. No subtitles, no captions, no text or writing anywhere in the frame."

# Roles, not fixed babies: every clip is a different baby (Google Flow can't repeat a face anyway).
# The opener always wears the Chair's tiny tie + reading glasses; the set and catchphrases are the brand.
ROLES = {
    "chair": {"voice": "a serious, deadpan little toddler voice",
              "prop": "wearing a white shirt collar and a tiny navy tie over the nappy, and small round wire reading glasses",
              "moves": ["taps one little finger slowly on the table and raises one eyebrow",
                        "peers over the top of the reading glasses straight at the camera",
                        "slaps one tiny palm flat on the table like a gavel",
                        "folds chubby arms and nods gravely",
                        "straightens the tiny tie with both hands, then looks into the lens"]},
    "zuri": {"voice": "a sassy, confident little toddler voice",
             "moves": ["sips from a sippy cup like an espresso, then gives the camera a slow side-eye",
                       "raises one eyebrow and purses the lips",
                       "sets a sippy cup down very deliberately",
                       "tilts the head and wags one tiny finger",
                       "leans back in a little chair, completely unimpressed"]},
    "ada": {"voice": "a calm, soft, wise little toddler voice",
            "moves": ["rests the chin on one hand and nods slowly",
                      "taps the temple with one tiny finger",
                      "steeples little fingers thoughtfully",
                      "gazes out of the window, then turns back to the lens",
                      "places both hands on the table and speaks very sincerely"]},
    "rocco": {"voice": "a loud, dramatic, theatrical little toddler voice",
              "moves": ["throws both arms in the air",
                        "clutches the chest theatrically",
                        "points at the camera in outrage",
                        "flops across the table, then sits bolt upright",
                        "slumps down in the chair in despair, then pops back up"]},
    "closer": {"voice": "a soft, sincere little toddler voice",
               "moves": ["leans forward with a small warm smile", "rests both hands calmly on the table",
                         "nods once, slowly", "looks straight into the lens with big sincere eyes"]},
}
BEAN = {"look": "a tiny newborn baby swaddled in a cream blanket, lying in a wicker bassinet",
        "gags": ["lets out a tiny loud burp", "hiccups once, loudly", "does a tiny sneeze",
                 "gives a huge slow yawn", "blows a little raspberry", "giggles softly",
                 "startles and flings both tiny arms up"]}

# 25 delegates: (he/she, look). Rotated so every clip in an episode is a different baby.
BABIES = [
    ("he", "a chubby 18-month-old East Asian baby boy with short spiky black hair, in a white nappy and a tiny grey cardigan"),
    ("she", "a chubby 2-year-old Black toddler girl with curly hair in two puffs tied with pink bows, a pink knitted cardigan over her white nappy"),
    ("she", "a 2-year-old toddler girl with wispy ginger hair and freckles, a mustard-yellow headband, a tiny green knitted vest over her white nappy"),
    ("he", "a 3-year-old toddler boy with big dark curls, a red superhero cape over a white vest and nappy"),
    ("he", "a chubby 1-year-old blond baby boy with a single curl on top, a tiny blue bow tie over his nappy"),
    ("she", "a 2-year-old South Asian toddler girl with a short black bob and tiny gold-coloured hair clips, a lilac romper"),
    ("he", "a chubby 18-month-old Black baby boy with a short neat afro, a tiny pinstripe waistcoat over his nappy"),
    ("she", "a 1-year-old baby girl with almost no hair and huge blue eyes, a white frilly bib like a cravat over her nappy"),
    ("he", "a 2-year-old Latino toddler boy with thick wavy brown hair, a tiny denim jacket over a white nappy"),
    ("she", "a chubby 2-year-old Middle Eastern toddler girl with long dark curls, a cream knitted jumper"),
    ("he", "a 3-year-old red-haired toddler boy with freckles, tiny round sunglasses pushed up on his head, a striped t-shirt and nappy"),
    ("she", "a 18-month-old East Asian baby girl with a tiny top-knot, a mint-green dungaree romper"),
    ("he", "a chubby 1-year-old mixed-race baby boy with soft curly brown hair, a tiny knitted beanie and a nappy"),
    ("she", "a 2-year-old Black toddler girl with neat cornrows and beads, a yellow sundress"),
    ("he", "a 2-year-old South Asian toddler boy with a side parting, a tiny checked shirt over his nappy"),
    ("she", "a chubby 1-year-old blonde baby girl with a big pink flower headband, a white nappy"),
    ("he", "a 3-year-old toddler boy with a buzz cut, a tiny orange hi-vis vest over a white vest and nappy"),
    ("she", "a 2-year-old Latina toddler girl with two braids, a tiny pearl-style toy necklace, a navy dress"),
    ("he", "a chubby 18-month-old baby boy with wild white-blond hair, a tiny tweed flat cap and a nappy"),
    ("she", "a 2-year-old toddler girl with short brown curls, tiny star-shaped toy glasses, a rainbow t-shirt"),
    ("he", "a 2-year-old East Asian toddler boy with a bowl haircut, a tiny navy blazer over his nappy"),
    ("she", "a chubby 18-month-old Black baby girl with a soft afro and a white headband, a lemon-yellow romper"),
    ("he", "a 1-year-old baby boy with chubby rosy cheeks and a dark curl, a tiny green bow tie and a nappy"),
    ("she", "a 3-year-old toddler girl with a long auburn ponytail, a tiny clipboard tucked under one arm, a blue pinafore"),
    ("he", "a 2-year-old Middle Eastern toddler boy with thick black hair and long eyelashes, a cosy brown jumper"),
]


CLIPS = 8   # chair + 6 wishes + closer = 64 s (over one minute: TikTok Creator Rewards eligible)


def pick_babies(i):
    return [BABIES[(i * 7 + k * 3) % 25] for k in range(CLIPS)]


# (title, hook_text, theme, parenting note, tags, opener, [(speaker, line) x3], closer)
EPISODES = [
    ("Babies held a meeting about bedtime", "The babies have notes on bedtime", "bedtime",
     "A predictable bedtime routine (bath, book, bed) helps young children settle and sleep better.",
     ["bedtime routine", "toddler sleep"],
     "This meeting is in session. Agenda item one: bedtime. It's been chaotic.",
     [("zuri", "I wish bedtime looked the same every night. Bath, book, bed. Surprises are for birthdays."),
      ("ada", "I fight sleep because I'll miss you. Stay a minute longer. Then I'll let go."),
      ("rocco", "You skipped three pages of the story last night! I noticed. I always notice!")],
     "Same routine every night. It's not boring to us. It's safe. Motion carried."),
    ("What babies wish you knew about tantrums", "What a tantrum really means", "tantrums",
     "Toddlers can't calm big feelings alone yet. A calm adult nearby (co-regulation) and naming the feeling help most.",
     ["tantrums", "toddler emotions"],
     "Order. Today we discuss what you call tantrums. We call them overwhelming.",
     [("rocco", "I'm not giving you a hard time. I'm HAVING a hard time. Big difference!"),
      ("zuri", "When you yell back, now there's two of us screaming. Who's the grown-up here?"),
      ("ada", "Name the feeling for me. You're angry. You're sad. Hearing it makes it smaller.")],
     "Stay calm and stay close. Your calm becomes our calm. Motion carried."),
    ("Babies filed a complaint about your phone", "Your phone vs. your baby", "parent phone use",
     "Babies learn through face-to-face back-and-forth. Frequent phone use interrupts those moments.",
     ["phone addiction", "screen time"],
     "This meeting is in session. Today's complaint: the glowing rectangle in your hand.",
     [("zuri", "I showed you my tower. You said wow without looking. Mm-hm. I saw that."),
      ("ada", "Your face is my favourite screen. When you look at your phone, I lose my show."),
      ("rocco", "I did a whole dance! A whole dance! And you missed it for an email!")],
     "Ten minutes, phone down, eyes on us. That's all we ask. Motion carried."),
    ("Babies explain why play is serious business", "Play is our job, actually", "play",
     "Child-led play builds language, problem-solving and emotional skills. Following your child's lead matters.",
     ["play", "child development"],
     "Order. Agenda item: play. Apparently some of you think it's a waste of time.",
     [("ada", "Play is my work. It's how I learn physics, words and feelings. Very serious business."),
      ("zuri", "Get on the floor with me. And let me be the boss of the game, for once."),
      ("rocco", "You keep turning my castle into a counting lesson! Just be the dragon!")],
     "Follow our lead fifteen minutes a day. You'll learn who we are. Motion carried."),
    ("The great park departure disaster", "Why leaving the park ends in tears", "transitions",
     "Young brains switch activities slowly. Countdown warnings before a change reduce meltdowns.",
     ["toddler meltdowns", "transitions"],
     "This meeting is in session. Today: the great park departure disaster.",
     [("rocco", "One second I'm on the swing, the next I'm in the car seat! No warning! Betrayal!"),
      ("zuri", "Give me a five-minute warning. Then two minutes. Then one more slide. Deal?"),
      ("ada", "My brain can't switch as fast as yours yet. I need a bridge, not a cliff.")],
     "Warn us before the change. Fewer meltdowns for everyone. Motion carried."),
    ("Why babies say NO to everything", "Why we say NO to everything", "choices",
     "Toddlers crave a little control. Offering two acceptable choices cuts power struggles.",
     ["toddler no", "power struggles"],
     "Order. Agenda: why we say no to absolutely everything. A briefing.",
     [("ada", "I say no because it's the only power I have. Give me some little choices."),
      ("zuri", "Red cup or blue cup? Suddenly I'm cooperative. It's not magic, darling. It's management."),
      ("rocco", "You never ask what I want to wear! Today I wanted the dinosaur! I'm in mourning!")],
     "Two choices, both ones you're happy with. Everybody wins. Motion carried."),
    ("Babies vs broccoli: the official report", "The broccoli war, explained", "picky eating",
     "Children often need many tastes of a new food before accepting it. Pressure usually backfires.",
     ["picky eater", "toddler food"],
     "This meeting is in session. Today's agenda: broccoli. And the war around it.",
     [("zuri", "You offered me peas twice and gave up. Try ten more times. I'm thinking."),
      ("ada", "When you beg me to eat, food becomes a fight. When you relax, I get curious."),
      ("rocco", "The carrots touched the pasta! Do you know what that does to a person?")],
     "You decide what's served. We decide how much. Keep dinners calm. Motion carried."),
    ("Stop calling babies clever (here's why)", "Stop saying 'clever'. Say this.", "praise",
     "Praising effort and strategy, rather than fixed traits, helps children keep going when things get hard.",
     ["praise", "growth mindset"],
     "Order. Agenda item: compliments. Specifically, the word clever.",
     [("ada", "Don't just say I'm clever. Say I tried hard. Then I'll keep trying when it's hard."),
      ("zuri", "Good job. Good job. Good job. Be specific, darling. What exactly was good?"),
      ("rocco", "You said I'm a natural at drawing! So I scribbled once badly and quit forever!")],
     "Praise our effort, not our labels. Effort we can control. Motion carried."),
    ("Yes, read the same book AGAIN", "Read it again. Here's why.", "reading",
     "Reading aloud every day grows vocabulary, and repeating favourite books is how young children learn.",
     ["reading to kids", "bedtime stories"],
     "This meeting is in session. Today's agenda: books. We have strong feelings.",
     [("zuri", "Yes, it's the same book again. I'm not bored. You're bored. Read it."),
      ("ada", "Every story you read me puts hundreds of new words in my head."),
      ("rocco", "Do the voices! The bear needs a bear voice! You did him like a newsreader!")],
     "Read with us every day. Even ten minutes. Best gift there is. Motion carried."),
    ("Babies are officially in favour of rules", "Babies voted FOR rules", "boundaries",
     "Warm but firm limits make children feel safe. Kind and consistent beats harsh or permissive.",
     ["boundaries", "gentle parenting"],
     "Order. Today's agenda: rules. Yes, the Committee is officially in favour of them.",
     [("ada", "When you say no and mean it, I feel safe. Wobbly rules make a wobbly world."),
      ("rocco", "I'll cry when you say no. I'll scream. Hold the line anyway. Lovingly!"),
      ("zuri", "If no turns into yes after ten minutes of whining, darling, I will whine.")],
     "Kind and firm, both at once. That's the sweet spot. Motion carried."),
    ("Don't compare me to the neighbour's baby", "Stop comparing us. Please.", "comparison",
     "Milestones have a wide normal range. Comparing children to siblings or peers can breed resentment.",
     ["milestones", "sibling rivalry"],
     "This meeting is in session. Agenda: being compared to the neighbour's baby.",
     [("rocco", "Oh, Oliver walks already? Wonderful! Maybe Oliver can live here then!"),
      ("ada", "Every child blooms on their own schedule. I'm not late. I'm me."),
      ("zuri", "Comparing me to my sister doesn't make me better. It makes me resent her. Mm-hm.")],
     "Compare us only to who we were yesterday. Motion carried."),
    ("Babies are tired of talking to your knees", "Get down to our level", "listening",
     "Getting down to eye level and really listening builds trust, so children keep talking as they grow.",
     ["listening", "connection"],
     "Order. Today's complaint: we spend all day talking to your knees.",
     [("zuri", "Get down to my level when you talk to me. Eyes here. Thank you."),
      ("ada", "If you listen to my small stories now, I'll tell you the big ones later."),
      ("rocco", "I was explaining the worm situation and you walked off! The worm situation!")],
     "Listen while our problems are small, and we'll talk when they're big. Motion carried."),
    ("What babies hear when parents argue", "We hear every argument", "conflict",
     "Children cope better with parental conflict when they also see it resolved calmly.",
     ["parents arguing", "family"],
     "This meeting is in session. A sensitive topic today: when Mum and Dad argue.",
     [("ada", "We hear everything. Even through the door. Even when you whisper-shout."),
      ("rocco", "When you fight, I think it's my fault. Is it my fault? Tell me it's not!"),
      ("zuri", "Fine, argue sometimes. Grown-ups do. But let us see you make up too.")],
     "Show us how to fix it. Then we learn love survives a storm. Motion carried."),
    ("Grown-ups who never say sorry", "When did YOU last say sorry?", "apologising",
     "When parents apologise and repair after a rough moment, children learn how to do it too.",
     ["apologise", "repair"],
     "Order. Agenda item: grown-ups who never say sorry. We've noticed.",
     [("zuri", "You made me say sorry to Leo. Fair. But you shouted at me yesterday. Hmm?"),
      ("ada", "When you apologise to me, I learn how to apologise. You're my textbook."),
      ("rocco", "You said sorry and gave me a cuddle and I forgave you instantly! I'm a professional!")],
     "Nobody's perfect. Fixing it matters more than never messing up. Motion carried."),
    ("Let babies do it themselves", "Let us do it ourselves", "independence",
     "Letting children try (and struggle a little) builds confidence and real skills.",
     ["independence", "toddler skills"],
     "This meeting is in session. Agenda: let us do it ourselves. Please.",
     [("ada", "When you zip my coat every time, I learn I can't. Let me struggle a little."),
      ("rocco", "It took me nine minutes to put on one shoe! Wrong foot! I was thriving!"),
      ("zuri", "Yes, I'll pour the milk badly. That's what cloths are for, darling.")],
     "Help a little, then step back. Watch us grow. Motion carried."),
    ("Babies demand more mud", "The case for mud", "outdoor play",
     "Outdoor, messy play builds coordination, curiosity and resilience.",
     ["outdoor play", "messy play"],
     "Order. Agenda item: mud. The Committee would like more of it.",
     [("rocco", "You put me in white clothes then panic when I find a puddle! It's a trap!"),
      ("ada", "Dirt, sticks, rain. Outside, my body learns things no screen can teach."),
      ("zuri", "The washing machine exists, darling. Let me jump.")],
     "Let us play outside every day. Messy kids are learning kids. Motion carried."),
    ("Babies confess about the tablet", "Babies on the tablet: a confession", "kids screen time",
     "Health bodies advise very limited, high-quality screen time for under-fives, ideally watched together.",
     ["screen time", "tablet kids"],
     "This meeting is in session. Agenda: the tablet. We have a confession.",
     [("zuri", "Yes, I scream when you take the tablet. That's exactly why there should be less of it."),
      ("ada", "I learn far more from your face talking to me than from any cartoon."),
      ("rocco", "Watch the show with me! Then we can talk about the singing potato together!")],
     "Less screen, more you. And when we watch, watch with us. Motion carried."),
    ("Hurry up, hurry up, hurry up", "Mornings, from a baby's view", "rushing",
     "Young children live in the present and can't rush. Building in buffer time prevents daily battles.",
     ["morning routine", "toddler"],
     "Order. Today's agenda: the morning rush. Hurry up, hurry up, hurry up.",
     [("rocco", "Every morning! Hurry, hurry, hurry! I'm two! I don't even know what late means!"),
      ("ada", "I live in this exact minute. That's not slow. That's being a child."),
      ("zuri", "Wake up ten minutes earlier, darling. It's cheaper than all this shouting.")],
     "Build in extra time. A calm morning makes a calm day. Motion carried."),
    ("Stop sneaking out at nursery drop-off", "Don't sneak out. Say goodbye.", "separation",
     "A short, clear goodbye ritual builds trust. Sneaking away can make separation anxiety worse.",
     ["separation anxiety", "nursery drop off"],
     "This meeting is in session. Agenda: sneaky goodbyes at nursery drop-off.",
     [("ada", "When you sneak away, I learn you can vanish. Say goodbye, even if I cry."),
      ("rocco", "I cried at drop-off, then had the best day of my life! Both are true!"),
      ("zuri", "Short goodbye, big hug, tell me when you're back. Then go. Don't hover.")],
     "A clear goodbye builds trust. You always come back. Motion carried."),
    ("The labels you put on babies", "Careful what you call us", "labels",
     "Children tend to live up (or down) to the labels they hear. Describe the behaviour, not the child.",
     ["labels", "self esteem"],
     "Order. Agenda: the labels you put on us in front of other people.",
     [("zuri", "You told the lady I'm shy. Now I'm shy, apparently. Thanks for that."),
      ("ada", "Call me naughty often enough and I'll believe it. Name the behaviour, not me."),
      ("rocco", "I'm not the difficult one! I'm the passionate one! There's a difference!")],
     "Careful with labels. Children grow into the words you choose. Motion carried."),
    ("Babies on the monster under the bed", "The monster IS real (to us)", "fears",
     "Fears are real to children even when the danger isn't. Taking them seriously helps children face them.",
     ["toddler fears", "bedtime fears"],
     "This meeting is in session. Today's agenda: the monster under the bed.",
     [("rocco", "There IS something under the bed! And you laughed! I could have been eaten!"),
      ("ada", "My fear is real to me, even if the monster isn't. Take it seriously."),
      ("zuri", "Check under the bed with me. Torch, please. Ten seconds. Problem solved.")],
     "Don't laugh off our fears. Help us face them. Motion carried."),
    ("A new baby arrived. Nobody asked us.", "Nobody consulted us about the new baby", "new sibling",
     "Older siblings often regress after a new baby. Short daily one-to-one time helps them feel secure.",
     ["new sibling", "sibling jealousy"],
     "Order. An urgent matter: a new baby has arrived. Nobody consulted the Committee.",
     [("rocco", "Everyone visits the new baby! Nobody asks how I'M coping! I'm the original!"),
      ("ada", "When I act younger, I'm asking if there's still room for me. Show me there is."),
      ("zuri", "Ten minutes a day, just me. No baby. I'll be much nicer about the whole thing.")],
     "Big brothers and sisters need their own time too. Motion carried."),
    ("The potty: a delicate matter", "Potty training, from our side", "potty training",
     "Children are ready for the potty at different ages. Patience works; pressure and shame backfire.",
     ["potty training", "toddler"],
     "This meeting is in session. Agenda: the potty. A delicate matter.",
     [("ada", "I'll use the potty when my body is ready, not when the neighbour's child did."),
      ("rocco", "I had ONE accident and you sighed so loudly! Do you know how that feels?"),
      ("zuri", "Stickers, cheering, calm. Mm-hm. Shame never trained anyone, darling.")],
     "Patience, no pressure, no shame. We'll get there. Motion carried."),
    ("Talk to babies. Constantly. Here's why.", "Talk to us. All day.", "language",
     "Back-and-forth 'serve and return' talk with babies builds the brain's language foundations.",
     ["baby talk", "language development"],
     "Order. Agenda: talking. We can't say much yet, but we're listening to everything.",
     [("ada", "When I babble, babble back. Every little conversation builds my brain."),
      ("zuri", "Narrate your day to me. Now we're putting on socks. Now we're cooking. Riveting."),
      ("rocco", "I said ba and you said ball! Do you know how proud I was? Do it again!")],
     "Talk with us all day. It's how we learn to talk back. Motion carried."),
    ("Babies have been tracking your empty threats", "We keep a list of empty threats", "consistency",
     "Small consequences that are actually followed through work better than big threats that aren't.",
     ["discipline", "consistency"],
     "This meeting is in session. Agenda: empty threats. We've been keeping a list.",
     [("zuri", "No more cartoons ever? Darling, we both know cartoons are back tomorrow."),
      ("ada", "Small consequences you actually keep work better than big ones you won't."),
      ("rocco", "You said we'd go to the park later! Later came! Later went! No park!")],
     "Say what you mean, then do what you say. Motion carried."),
    ("Babies held a meeting about YOU", "This one's about you, parents", "parent wellbeing",
     "Parents' rest and support matter. Asking for help is good for the whole family.",
     ["parent burnout", "self care"],
     "Order. Today the Committee wishes to discuss you. Yes, you.",
     [("ada", "You can't pour from an empty cup. Rest isn't selfish. It's for us too."),
      ("zuri", "Eat something that isn't my leftover crusts, darling. Sit down. Breathe."),
      ("rocco", "You were crying in the kitchen. I saw. You don't have to be strong every second.")],
     "Ask for help when you need it. A happy parent is our favourite thing. Motion carried."),
    ("Babies copy EVERYTHING you do", "We copy everything. Everything.", "modelling",
     "Children learn more from what parents do than from what they say.",
     ["role model", "kids copy parents"],
     "This meeting is in session. Agenda: we copy everything you do. Everything.",
     [("rocco", "You said a bad word in traffic and now it's my favourite word!"),
      ("zuri", "You tell me to be kind, then you're rude to the waiter. Hmm. Interesting."),
      ("ada", "I don't do what you say. I do what you do. Choose wisely.")],
     "You're our first teacher. We're always watching. Motion carried."),
    ("Babies on forced hugs at family parties", "Let us choose how we say hello", "body autonomy",
     "Letting children choose a hug, wave or high five teaches that their body belongs to them.",
     ["consent for kids", "family gatherings"],
     "Order. Agenda item: forced hugs at family gatherings. A sensitive subject.",
     [("zuri", "Auntie wants a kiss? Mm-hm. Can I offer a high five instead?"),
      ("ada", "When you let me choose how I say hello, you teach me my body is mine."),
      ("rocco", "I love Grandad! I just don't want a cuddle right this second! Both can be true!")],
     "A hug, a wave, or a high five. Let us choose. Motion carried."),
    ("The one request that changes everything", "One tiny request. Huge difference.", "quality time",
     "A few minutes of daily, undivided one-to-one time strengthens connection and behaviour.",
     ["quality time", "connection"],
     "This meeting is in session. Today: one simple request that changes everything.",
     [("ada", "Ten minutes a day, just you and me, no phone. That's my whole wish."),
      ("rocco", "I don't need a theme park! I need you on the floor with my trains!"),
      ("zuri", "Put it in your calendar, darling. Between the emails. I'll wait.")],
     "Small daily moments beat big expensive days. Motion carried."),
    ("The final item: love", "The most important item", "unconditional love",
     "Children thrive when they know they are loved for who they are, even on their hardest days.",
     ["unconditional love", "parenting"],
     "Order. The final item, and the most important one. Love.",
     [("zuri", "Love me on my worst days too. Those are the days I need it most."),
      ("ada", "Even when you're cross about what I did, show me you still love who I am."),
      ("rocco", "Tell me again tonight. I know you love me. I just like hearing it!")],
     "That's all, Mum and Dad. You're doing better than you think. Meeting adjourned."),
]

# 3 extra wishes per meeting (sassy zuri / wise ada / dramatic rocco), slotted in after the first three
EXTRA = [
 [("ada", "Dim the lights an hour before bed. My body reads darkness like a bedtime story."),
  ("rocco", "One more glass of water! One more cuddle! I'm not stalling! I'm negotiating!"),
  ("zuri", "And no wild games right before bed, darling. You wind me up, you deal with it.")],
 [("zuri", "Don't bribe me to stop crying, darling. I will learn. I learn very fast."),
  ("ada", "After the storm, hold me. Then we can talk about what happened."),
  ("rocco", "And please don't laugh while I'm melting down! It's a serious moment! For me!")],
 [("rocco", "I said Mummy eleven times! ELEVEN! I counted on my fingers! Well, some of them!"),
  ("zuri", "And the phone at dinner? Mm-hm. Dinner is a meeting. Phones off."),
  ("ada", "I copy everything you do. If you stare at screens, guess what I'll want.")],
 [("zuri", "I don't need fancy toys. A cardboard box and you? Premium entertainment."),
  ("ada", "When I play pretend, I'm practising being a person. Join me."),
  ("rocco", "You said five more minutes three times! That's fifteen minutes I was promised!")],
 [("ada", "Tell me what comes next. When I know the plan, I can let go of this one."),
  ("rocco", "Make leaving a game! Race me to the car! I'll win and forget I was sad!"),
  ("zuri", "Let me bring a toy along when we leave. Negotiations go much smoother.")],
 [("zuri", "Ask me to help, don't order me. Watch my attitude improve, darling."),
  ("rocco", "I wanted to press the lift button! It was MY button! Every single day!"),
  ("ada", "If I choose it, I own it. Then I'm much less likely to fight it.")],
 [("ada", "If you eat your vegetables happily, I'll get curious. I watch your face."),
  ("zuri", "Let me help cook, darling. I'm far more likely to eat what I made."),
  ("rocco", "You hid spinach in my pancakes! I found out! My trust is broken!")],
 [("zuri", "Don't praise every little thing, darling. Then it stops meaning anything."),
  ("rocco", "When I fail, don't panic! Say let's try again! Then I won't panic either!"),
  ("ada", "Ask me how I did it. Then I'll start thinking about how I did it.")],
 [("rocco", "Pick books with big feelings! Dragons! Storms! Lost teddy bears! Drama!"),
  ("ada", "Stop and ask me what will happen next. That's when my brain lights up."),
  ("zuri", "And let me turn the pages. I'm in charge of pacing, darling.")],
 [("zuri", "Same rules from both of you, please. If Daddy says no, Mummy can't say yes."),
  ("ada", "Explain the rule simply, once. Then stick to it. That's how I learn it."),
  ("rocco", "You can say no kindly! You can hold my hand and still say no!")],
 [("ada", "Every child's milestones are different. If you're worried, ask a doctor, not the internet."),
  ("rocco", "My cousin talks more? Fine! I'm saving my words for something important!"),
  ("zuri", "Celebrate my little wins too, darling. I learned to wave! That's huge.")],
 [("rocco", "Ask me about my day! I had a feud with a pigeon! It's very complicated!"),
  ("zuri", "Put the phone face down when I'm talking. I notice, darling. Every time."),
  ("ada", "Repeat back what I said. Then I know you really heard me.")],
 [("zuri", "Keep your voices low, darling. Words hit us harder than you think."),
  ("ada", "Never ask us to choose sides. We love you both, completely."),
  ("rocco", "If you're cross with each other, tell me it's not about me! Out loud! Please!")],
 [("ada", "A real sorry says what went wrong and how to fix it. Teach me that."),
  ("zuri", "And don't make me say sorry while I'm still furious, darling. Give me a minute."),
  ("rocco", "You stepped on my drawing and said oops! Oops is not a full apology!")],
 [("zuri", "Let me dress myself. Yes, the tutu with the wellies. It's a statement, darling."),
  ("ada", "Give me small jobs. Setting spoons, feeding the cat. I want to be useful."),
  ("rocco", "I want to carry the shopping! The heavy bag! Fine, the light one!")],
 [("ada", "When I climb, I'm learning what my body can do. Watch, don't panic."),
  ("rocco", "You said don't touch the snail! But he LOOKED at me! We're friends now!"),
  ("zuri", "Bring spare clothes, darling. Then we can both relax.")],
 [("ada", "Screens before bed keep my brain awake. Books put it to sleep."),
  ("zuri", "Don't use the tablet to calm me down every time, darling. Teach me other ways."),
  ("rocco", "The tablet died and I screamed! Then I found a box and it was GREAT!")],
 [("zuri", "Lay out my clothes the night before, darling. Fewer negotiations at dawn."),
  ("rocco", "I can't find my other shoe! It's not lost! It's on an adventure!"),
  ("ada", "When you rush me, I freeze. When you give me time, I flow.")],
 [("ada", "Tell me who'll pick me up, and when. Knowing helps me feel brave."),
  ("zuri", "And don't hover at the window, darling. Go. I've got a busy day."),
  ("rocco", "When you come back, tell me you missed me! Dramatically! I need it!")],
 [("rocco", "Call me brave! Call me kind! Call me the dragon tamer! I'll grow into it!"),
  ("ada", "Tell me what I did well instead. I'll do more of that."),
  ("zuri", "Don't call me the naughty one in front of my sister, darling. She's taking notes.")],
 [("ada", "Read me stories about being brave. Stories let me practise courage."),
  ("zuri", "Don't push me to hug the scary clown, darling. My fear, my pace."),
  ("rocco", "Leave a little light on! Monsters hate light! Everyone knows this!")],
 [("zuri", "Let me hold the baby. Supervised, darling. I'm not a monster."),
  ("ada", "Tell me I'm a big brother or big sister like it's a promotion. It is."),
  ("rocco", "The baby cries and everyone runs! I cried and got one biscuit! Inequality!")],
 [("rocco", "The big toilet is a monster! It roars! I need a small one, please!"),
  ("ada", "Accidents are part of learning. Like falling down when I learned to walk."),
  ("zuri", "Let me watch how it's done, darling. How else would I know?")],
 [("zuri", "Sing to me. Even badly. Especially badly. I don't judge."),
  ("rocco", "When I point and grunt, give me the word! I'm trying! Very hard!"),
  ("ada", "Name everything we see. Dog. Bus. Moon. Every word is a gift.")],
 [("rocco", "You said no sweets, then Grandma gave me sweets! Who's in charge here?!"),
  ("ada", "When rules change every day, I test them every day. Be steady."),
  ("zuri", "If you count to three, darling, finish at three. Not three and a half.")],
 [("zuri", "Let someone else hold me for an hour, darling. Take a nap."),
  ("rocco", "Have a bath! A long one! I'll be fine! Probably! Mostly!"),
  ("ada", "When you're calm, I'm calm. Looking after you is looking after me.")],
 [("ada", "When you calm down by breathing slowly, I learn to breathe slowly too."),
  ("zuri", "If you want me to say please, darling, I need to hear it too."),
  ("rocco", "You ate cake for breakfast once! Once! I saw it! I have evidence!")],
 [("ada", "Use the real names for body parts. It helps me speak up if something's wrong."),
  ("zuri", "Ask before tickling, darling. And stop when I say stop. Even if I'm laughing."),
  ("rocco", "I gave Granny a wave and she cried! It was a GOOD wave! A great wave!")],
 [("zuri", "Laugh with me. Silly voices, terrible dancing. Best ten minutes of my day."),
  ("ada", "When you're fully with me, I feel it. Even if it's only a few minutes."),
  ("rocco", "Take me on a date! The park! The swings! Just us! No sister!")],
 [("ada", "Notice me when I'm quiet too. Love isn't only for the loud moments."),
  ("zuri", "Say you love me even after you've told me off, darling. Especially then."),
  ("rocco", "When I'm grown and grumpy, remember this! Remember me in my cape!")],
]


MUSIC = ["playful pizzicato", "boardroom jazz", "gentle music box", "playful pizzicato", "light marimba"]
CAMERA_OPEN = ["slow push-in from a medium shot", "static medium shot from across the table",
               "low angle medium shot, slow push-in", "static medium close-up"]
CAMERA_MID = ["static medium close-up", "slow push-in on the face", "medium shot, gentle handheld drift",
              "close-up, slight handheld drift"]


def prompt(look, pron, move, voice, line, camera, extra=""):
    sub = pron.capitalize()
    return (f"{STYLE}. {look[0].upper() + look[1:]}, {SET}. Camera: {camera}. {sub} {move}, then says in "
            f"{voice}: \"{line}\"{extra} Ambient: quiet room tone, soft clock tick. {TAIL}")


def build():
    eps = []
    for i, (title, hook, theme, note, tags, opener, wishes, closer) in enumerate(EPISODES):
        n = i + 1
        babies = pick_babies(i)
        ids = [f"d{(i * 7 + k * 3) % 25 + 1:02d}" for k in range(CLIPS)]
        extra = list(EXTRA[i])
        while extra[0][0] == wishes[-1][0]:      # never the same comic tone twice in a row
            extra = extra[1:] + extra[:1]
        plan = [("chair", opener)] + list(wishes) + extra + [("closer", closer)]
        shots = []
        for k, ((role, line), (pron, look), cid) in enumerate(zip(plan, babies, ids)):
            r = ROLES[role]
            if role == "chair":
                look = look.replace(" in a white nappy and", " in a white nappy,") + ", " + r["prop"]
                cam = CAMERA_OPEN[i % 4]
            elif role == "closer":
                cam = "slow push-in to a medium close-up"
            else:
                cam = CAMERA_MID[(i + k) % 4]
            mv = r["moves"][(i + k) % len(r["moves"])]
            extra, chars, sfx = "", [cid], "quiet room tone"
            if role == "closer":
                gag = BEAN["gags"][i % len(BEAN["gags"])]
                extra = (f" Beside the table, {BEAN['look']}, {gag} right after the last word, and the speaker "
                         f"glances at the newborn, then back at the camera.")
                chars, sfx = [cid, "bean"], f"newborn {gag.split(' ', 1)[-1]}"
                mv_desc = f"{mv}; the newborn {gag} after the last word"
            else:
                mv_desc = mv
            shots.append({"n": k + 1, "dur": 8, "loc": "boardroom", "chars": chars, "role": role,
                          "keyframe": f"{look}, {SET}", "action": mv_desc, "camera": cam,
                          "lines": [{"c": cid, "t": line, "tone": r["voice"]}], "sfx": sfx,
                          "flow_prompt": prompt(look, pron, mv, r["voice"], line, cam, extra)})
        eps.append({
            "id": f"CC-{n:03d}", "number": n, "theme": theme,
            "title": f"{title} #shorts", "logline": f"{theme.capitalize()}: {note}",
            "hook_text": hook,
            "description": (f"The Crib Committee is in session. Today: {theme}.\n\n"
                            f"Parenting note: {note}\n\n"
                            "New babies, same complaints. Which committee member is your little one? Tell us below."),
            "tags": tags + ["parenting", "parenting tips", "toddlers", "babies", "funny babies", "crib committee"],
            "music": MUSIC[i % len(MUSIC)],
            "parenting_note": note,
            "shots": shots,
            "loop_note": "the closing line and the newborn's gag end the meeting; tomorrow a new delegation takes the seats",
        })
    return eps


def bible():
    return {
        "channel_id": "cribcommittee",
        "show_title": "The Crib Committee",
        "tagline": "Babies have notes for their parents.",
        "audience": "parents and carers (adults). NOT made for kids.",
        "format": "A board meeting run by babies. Every clip is a different baby (new delegation every day, no names). The Chair (tiny tie + reading glasses) opens, six members make one wish each, an eighth member closes, the newborn intern delivers the gag. 8 x 8 s = 64 s.",
        "source": "flow",
        "episode_id_prefix": "CC",
        "target_seconds": [60, 70],
        "max_seconds": 90,
        "style_prompt": STYLE,
        "set": SET,
        "audio_prompt": TAIL,
        "negative_prompt": "text, writing, name plates, signs, logos, real identifiable people, unsafe situations",
        "characters": {**{f"d{j + 1:02d}": {"name": f"Delegate {j + 1:02d}", "ref_prompt": look, "pronoun": pron,
                                            "voice": "toddler voice set per role", "tts_voice_id": ""}
                          for j, (pron, look) in enumerate(BABIES)},
                       "bean": {"name": "The Intern", "ref_prompt": BEAN["look"], "voice": "baby noises only",
                                "tts_voice_id": ""}},
        "roles": {k: {kk: vv for kk, vv in v.items() if kk != "moves"} for k, v in ROLES.items()},
        "locations": {"boardroom": SET},
        "content_rules": [
            "Audience is parents: humour is for adults, the advice is mainstream child-development guidance (no fringe claims, no medical advice).",
            "No names: every clip is a different baby (New babies, same complaints). Only the opener's tiny tie + reading glasses mark the Chair.",
            "Wish deliveries rotate three comic tones: sassy (zuri), wise (ada), dramatic (rocco).",
            "Babies are always safe: seated, supervised setting, nothing a real child could copy dangerously.",
            "Never mock real parents or children; the joke is babies behaving like executives.",
            "Each line <= 18 words; the spoken line must appear exactly in flow_prompt.",
            "No writing in frame (name plates and signs come out garbled).",
        ],
        "music_moods": ["playful pizzicato", "boardroom jazz", "gentle music box", "light marimba"],
        "made_for_kids": False,
        "youtube_category": "22",
        "nonverbal": False,
        "review_hours": 11,
        "ai_disclosure": "All babies in this video are AI-generated characters. Parenting notes are general information, not professional advice.",
        "overlays": {"hook": True, "captions": True},
        "flow": {"model": "Veo 3.1 Lite", "aspect": "9:16", "outputs_per_prompt": 1, "clip_seconds": 8,
                 "credits_per_clip": 10, "daily_free_credits": 50,
                 "clips_per_episode": CLIPS, "accounts": ["Crib account 1", "Crib account 2"]},
        "compilation_title": "{show} | {label} - {n} Meetings Back to Back",
        "compilation_tags": ["parenting", "funny babies", "parenting tips"],
        "compilations": {"weekly": True, "monthly": True},
    }


if __name__ == "__main__":
    (CH / "episodes").mkdir(parents=True, exist_ok=True)
    (CH / "channel.json").write_text(json.dumps(bible(), indent=2, ensure_ascii=False) + "\n")
    eps = build()
    for a in (0, 15):
        (CH / "episodes" / f"eps_{a + 1:03d}-{a + 15:03d}.json").write_text(
            json.dumps({"episodes": eps[a:a + 15]}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(eps)} episodes to {CH}")
