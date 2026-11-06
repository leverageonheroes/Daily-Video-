#!/usr/bin/env python3
"""Builds channels/elders/channel.json and episodes 001-030 (Ask The Elders, Google Flow channel).

Each episode = 5 different elders x 8 s Veo 3.1 Lite clips = 40 s.
Every shot carries a ready-to-paste `flow_prompt`, so a human can generate it in Google Flow in seconds.
Re-run safely: python tools/generators/build_elders_001-030.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "channels" / "elders"

# ---------------------------------------------------------------- locations
LOCATIONS = {
    "farm_fence": ("old wooden fence at the edge of a green field, big sky at golden hour, cattle far in the soft-focus background",
                   "gentle wind, distant birdsong"),
    "veranda": ("shaded veranda of a family house with a mango tree, warm tropical afternoon light, patterned cushions",
                "cicadas, distant children playing"),
    "porch": ("wooden front porch of a weathered white house at golden hour, rocking chair, porch swing, fields behind",
              "crickets, creak of the rocking chair"),
    "garden": ("lush back garden with roses and vegetable beds, late afternoon sun, watering can nearby",
               "birdsong, bees humming"),
    "city_balcony": ("small apartment balcony crowded with potted plants overlooking a city at dusk, warm window light behind",
                     "soft distant city traffic"),
    "kitchen": ("warm cluttered home kitchen, morning light through the window, steaming kettle, old patterned tiles",
                "kettle simmering, clock ticking"),
    "fishing_dock": ("wooden fishing jetty at dawn, mist drifting over a calm loch, small rowing boat tied up",
                     "water lapping, a distant gull"),
    "tea_house": ("small traditional tea house with low wooden tables, paper screens, steam rising from a clay teapot",
                  "quiet room tone, tea being poured"),
    "workshop": ("woodworking shed with hand tools hanging on the wall, sawdust floating in a warm lamp beam",
                 "quiet room tone, faint radio far away"),
    "diner": ("old roadside diner booth by the window, mug of coffee, soft neon blur behind",
              "low diner chatter, cutlery clinks"),
    "market": ("busy outdoor fruit and vegetable market stall, colourful produce, shoppers softly blurred behind",
               "market chatter, distant vendor calls"),
    "park_bench": ("park bench under golden autumn trees, leaves drifting down, soft afternoon light",
                   "leaves rustling, distant children"),
    "allotment": ("allotment plot with a small green shed, cabbages and runner beans, overcast English sky",
                  "wind, a robin singing"),
    "living_room": ("cosy living room armchair, knitted blanket, framed family photos on the wall, warm lamp light",
                    "quiet room tone, clock ticking"),
    "beach": ("seaside promenade at sunset, gentle waves behind, wind moving the hair slightly",
              "waves, gentle wind"),
    "piano_room": ("elegant sitting room with an upright piano covered in family photographs, lamp light",
                   "quiet room tone"),
    "barbershop": ("old-fashioned barbershop with leather chairs and long mirrors, warm tungsten light",
                   "soft radio, scissors snipping in the background"),
    "window_rain": ("armchair beside a large window with rain running down the glass, soft grey light, cup of tea on the sill",
                    "rain on the window"),
    "harbour": ("small wooden fishing boat moored in a sunny Mediterranean harbour, nets, white houses behind",
                "gulls, water lapping"),
    "library": ("quiet library corner with tall wooden bookshelves, green reading lamp, dust floating in the light",
                "deep quiet, a page turning"),
}

# ---------------------------------------------------------------- elders (recurring cast)
# id: (age, he/she, look, location, accent)
ELDERS = {
    "e01": (84, "he", "an 84-year-old white British farmer, flat cap, tweed jacket, grey stubble, deep laugh lines", "farm_fence", "a gentle Yorkshire accent"),
    "e02": (79, "she", "a 79-year-old Nigerian grandmother, colourful ankara headwrap and matching dress, warm round face", "veranda", "a warm Nigerian accent"),
    "e03": (88, "he", "an 88-year-old Black American man, neat silver beard, brown cardigan, reading glasses on a chain", "porch", "a slow Southern American drawl"),
    "e04": (91, "she", "a 91-year-old Irish woman, short white curls, floral blouse, gardening gloves", "garden", "a soft Irish accent"),
    "e05": (82, "he", "an 82-year-old Indian man, white kurta, thin wire glasses, grey moustache", "city_balcony", "a gentle Indian accent"),
    "e06": (86, "she", "an 86-year-old Jamaican woman, silver locs tied up, bright yellow blouse, gold hoop earrings", "kitchen", "a warm Jamaican accent"),
    "e07": (77, "he", "a 77-year-old Scottish fisherman, full white beard, cream wool fisherman's jumper", "fishing_dock", "a Scottish accent"),
    "e08": (93, "she", "a 93-year-old Japanese woman, silver hair in a neat bun, simple grey cardigan", "tea_house", "soft Japanese-accented English"),
    "e09": (80, "he", "an 80-year-old Italian craftsman, white hair swept back, waistcoat, rolled-up shirt sleeves", "workshop", "an Italian accent"),
    "e10": (85, "she", "an 85-year-old white American woman, silver bob, denim shirt, turquoise necklace", "diner", "a Midwestern American accent"),
    "e11": (89, "he", "an 89-year-old Ghanaian man, short white hair, smock with kente trim", "market", "a Ghanaian accent"),
    "e12": (78, "she", "a 78-year-old Chinese woman, short grey hair, jade bracelet, quilted jacket", "park_bench", "gentle Chinese-accented English"),
    "e13": (83, "he", "an 83-year-old Welsh man, bald with white hair at the sides, knitted cardigan", "allotment", "a Welsh accent"),
    "e14": (90, "she", "a 90-year-old Indian woman, cream saree, long silver braid", "living_room", "an Indian accent"),
    "e15": (81, "he", "an 81-year-old Mexican man, straw hat, white moustache, checked shirt", "beach", "a Mexican accent"),
    "e16": (87, "she", "an 87-year-old elegant English woman, pearl necklace, navy cardigan, silver hair set in waves", "piano_room", "a refined English accent"),
    "e17": (92, "he", "a 92-year-old Black British Caribbean gentleman, trilby hat, smart grey suit jacket", "barbershop", "a London Caribbean accent"),
    "e18": (76, "she", "a 76-year-old Polish woman, patterned headscarf, knitted shawl", "window_rain", "a Polish accent"),
    "e19": (84, "he", "an 84-year-old Greek man, white curly hair, white linen shirt, worry beads in hand", "harbour", "a Greek accent"),
    "e20": (80, "she", "an 80-year-old Filipino woman, short black-and-grey hair, floral dress", "veranda", "a Filipino accent"),
    "e21": (95, "he", "a 95-year-old thin white English gentleman, tweed waistcoat, pocket watch chain", "library", "a soft upper-class English accent"),
    "e22": (82, "she", "an 82-year-old Kenyan woman, short grey afro, beaded necklace, knitted shawl", "garden", "a Kenyan accent"),
    "e23": (86, "he", "an 86-year-old Pakistani man, neat white beard, grey waistcoat over a shalwar kameez", "city_balcony", "a Pakistani accent"),
    "e24": (79, "she", "a 79-year-old African American woman, silver twist-out hair, silk scarf", "porch", "a warm Southern American accent"),
    "e25": (88, "he", "an 88-year-old Irish man, tweed flat cap, worn wool coat", "window_rain", "an Irish accent"),
}
ORDER = sorted(ELDERS)

ONES = "zero one two three four five six seven eight nine".split()
TENS = {7: "seventy", 8: "eighty", 9: "ninety"}


def age_words(n):
    t, o = divmod(n, 10)
    return TENS[t] + ("" if o == 0 else "-" + ONES[o])


# ---------------------------------------------------------------- episodes
# (theme, title, hook_text, description, tags, [5 lines]); line 1 may contain {age}
EPISODES = [
    ("money", "What 80-year-olds wish they'd done with money #shorts", "Money advice from 80-year-olds",
     "Five elders on what they'd do differently with money.",
     ["money advice", "life lessons", "elders", "personal finance", "wisdom"],
     ["I'm {age}. I earned good money my whole life. Here's what I'd do differently.",
      "Buy time, not things. Every gadget I bought is in a landfill. My trips are still in me.",
      "Pay yourself first. Ten percent of every pay packet, before anyone else touches it.",
      "Only lend money you're happy to call a gift. I lost two friends learning that.",
      "And don't save all your happiness for retirement. Half my friends never got there."]),
    ("love", "What a 60-year marriage teaches you about love #shorts", "60 years married. Listen.",
     "Five elders on what really keeps love alive.",
     ["love advice", "marriage", "relationships", "life lessons", "elders"],
     ["I'm {age}. Married sixty-one years. Here's what nobody tells you about love.",
      "Love is a decision you make on the days you don't feel it.",
      "Never go to bed trying to win. Go to bed trying to understand.",
      "Marry someone who's kind to waiters. That's how they'll treat you in twenty years.",
      "And say it out loud. I thought she knew. You never know how many days are left."]),
    ("regret", "The regrets almost everyone has at 90 #shorts", "The regrets everyone shares",
     "Five elders on the regrets they hear again and again.",
     ["regrets", "life lessons", "elders", "motivation", "wisdom"],
     ["I'm {age}. I've watched a lot of friends say goodbye. They all regret the same things.",
      "I worried about what people thought. Those people never thought about me at all.",
      "I waited for the perfect moment. It never came. The ordinary moments were the good ones.",
      "I didn't call my brother for nine years, over something I can't even remember.",
      "If something scares you and excites you at the same time, that's your answer. Go."]),
    ("work", "Work advice from people who already retired #shorts", "45 years of work, in 40 seconds",
     "Five retirees on what actually mattered at work.",
     ["career advice", "work life balance", "retirement", "life lessons", "elders"],
     ["I'm {age}. Forty-five years of work. Here's what actually mattered.",
      "Nobody at my funeral will mention my sales figures. Not one person.",
      "The company replaced me in two weeks. My kids couldn't replace the evenings I missed.",
      "Learn a skill people will pay for. Titles disappear. Skills don't.",
      "Work hard, yes. But go home on time. The work will still be there. They might not."]),
    ("health", "What 90-year-olds wish they'd done for their body #shorts", "Do this for your body now",
     "Five elders on the health habits they wish they'd started sooner.",
     ["healthy habits", "aging", "life lessons", "elders", "wellbeing"],
     ["I'm {age}. I'd trade every trophy I own for the knees I had at thirty.",
      "Walk every single day. Not for your weight. For your mind.",
      "Look after your teeth. Nobody warns you how much a smile costs at eighty.",
      "Sleep is not lazy. I wore my tiredness like a medal. It was a bill.",
      "Your body carries you your whole life. Stop treating it like a rental car."]),
    ("friendship", "Friendship lessons from the very old #shorts", "What old friends teach you",
     "Five elders on keeping the friends that matter.",
     ["friendship", "life lessons", "elders", "loneliness", "wisdom"],
     ["I'm {age}. Most of my friends are gone now. Here's what I learned from them.",
      "You don't need many friends. You need two who'll answer the phone at three in the morning.",
      "Friendships die from silence, not arguments. Send the text. Make the call.",
      "Keep some friends younger than you. Otherwise, one day, you'll have none left.",
      "Go to the reunion. Go to the wedding. Go. Showing up is the whole thing."]),
    ("money", "Money mistakes they still think about at 85 #shorts", "Rich, then broke. The lessons.",
     "Five elders on the money mistakes that taught them the most.",
     ["money mistakes", "debt", "personal finance", "life lessons", "elders"],
     ["I'm {age}. I've been rich and I've been broke. Broke taught me more.",
      "If you can't buy it twice, you can't afford it. That rule saved my house.",
      "Never sign anything the day someone pressures you. A good deal waits till tomorrow.",
      "The neighbours with the fancy cars? Most were in debt. Don't compete with them.",
      "Rich isn't what you earn. It's how much of your life you get to choose."]),
    ("love", "Heartbreak advice from people who survived it #shorts", "For anyone with a broken heart",
     "Five elders on getting through heartbreak.",
     ["heartbreak", "breakup advice", "love", "life lessons", "elders"],
     ["I'm {age}. My heart's been broken three times. Here's what helped.",
      "The person who leaves is not the one who decides your worth.",
      "Don't fill the empty space too fast. Sit with it. It teaches you what you need.",
      "I married the second love of my life. Best thing that ever happened to me.",
      "You'll laugh again. I promise you. I'm proof. Give it time."]),
    ("regret", "Stop doing these things at 20, say 80-year-olds #shorts", "Stop doing this. Today.",
     "Five elders on the habits they wish they'd dropped decades earlier.",
     ["self improvement", "confidence", "life lessons", "elders", "advice"],
     ["I'm {age}. If I could go back, I'd stop doing these things at twenty.",
      "Stop apologising for taking up space. You're allowed to be in the room.",
      "Stop explaining yourself to people determined to misunderstand you.",
      "Stop waiting for permission. Nobody is coming to tell you it's your turn.",
      "And stop saying one day. I've got a whole drawer full of one days."]),
    ("work", "Career advice from people with 50 years' experience #shorts", "Career advice you won't get at work",
     "Five elders with decades of work behind them share what they'd tell a 25-year-old.",
     ["career advice", "job advice", "pay rise", "life lessons", "elders"],
     ["I'm {age}. I've had eleven jobs. Here's what I'd tell a twenty-five-year-old.",
      "Ask for the raise. The worst they say is no, and you'll know where you stand.",
      "Your boss is not your family. Be loyal to people, not companies.",
      "The quiet one who listens gets promoted. Talk less in meetings. Mean every word.",
      "If you dread Sunday nights for a year, that's not a job. That's a sentence."]),
    ("health", "Simple habits that kept them going past 85 #shorts", "Still climbing stairs at 90",
     "Five elders share the small daily habits that kept them going.",
     ["daily habits", "longevity", "healthy aging", "life lessons", "elders"],
     ["I'm {age} and I still climb my own stairs. Here's how.",
      "I eat dinner early and small. Breakfast like a king, supper like a pauper.",
      "Get your hands in the soil. My garden kept me cheerful through the hardest years.",
      "Laugh every day, even at nothing. It's the cheapest medicine there is.",
      "And keep learning. I started piano at seventy-eight. My brain thanked me."]),
    ("family", "What they wish they'd done with their parents #shorts", "Call your parents after this",
     "Five elders on the time with their parents they wish they could get back.",
     ["parents", "family", "life lessons", "elders", "emotional"],
     ["I'm {age}. My parents have been gone forty years. I'd give anything for one more Sunday.",
      "Record their voices. One day you'll forget how they laughed. I did.",
      "Ask about their lives before you. My mother had a whole story I never heard.",
      "Forgive them while they're alive. Forgiving a gravestone is much harder.",
      "Call your mum. Right now. This video can wait."]),
    ("money", "Money rules school never taught you #shorts", "Money rules school skipped",
     "Five elders on the money basics they wish they'd learned young.",
     ["money tips", "saving money", "financial literacy", "life lessons", "elders"],
     ["I'm {age}. Here are the money rules I wish school had taught me.",
      "Start saving young. Money left alone for forty years grows in ways that feel like magic.",
      "Lifestyle creep is a thief. Every raise, I just bought a bigger cage.",
      "Keep six months of living money aside. It turns a disaster into an inconvenience.",
      "Money can't buy happiness. But being broke at seventy can certainly buy misery."]),
    ("love", "How to know they're the one, from couples married 50+ years #shorts", "How you know they're the one",
     "Five elders married for decades on how you really know.",
     ["the one", "relationships", "marriage advice", "love", "elders"],
     ["I'm {age}. Fifty-four years with the same person. Here's how you know.",
      "You can sit in silence with them, and it doesn't feel empty.",
      "They're proud of you when you're not even in the room.",
      "They fight the problem with you. Never you.",
      "Choose the one who makes you laugh. Looks fade. The laughing doesn't."]),
    ("regret", "Advice for your 30s from people in their 90s #shorts", "If you're in your 30s, listen",
     "Five elders speak to anyone in their thirties who feels behind.",
     ["30s", "feeling behind", "life lessons", "elders", "motivation"],
     ["I'm {age}. If you're in your thirties, listen closely.",
      "You're not behind. There's no schedule. I started my business at fifty-two.",
      "Your parents are getting older faster than you think. Visit more.",
      "Put the phone down sometimes. Be bored. Boredom is where the good ideas live.",
      "You'll never be this young again. Wear the dress. Book the flight."]),
    ("work", "What building a business from nothing really costs #shorts", "What success really costs",
     "Five elders who built something share what it took, and what it cost.",
     ["entrepreneur", "business advice", "success", "life lessons", "elders"],
     ["I'm {age}. I built a business from nothing. Here's what it really costs.",
      "Success came from showing up on the days I didn't want to. That's the whole secret.",
      "Your reputation arrives before you do. Guard it like money.",
      "Hire people better than you, then get out of their way.",
      "And don't trade your health for wealth. You'll spend the wealth buying it back."]),
    ("aging", "What getting old actually feels like #shorts", "What being 90 really feels like",
     "Five elders describe what getting old really feels like from the inside.",
     ["getting old", "aging", "perspective", "life lessons", "elders"],
     ["I'm {age}. Let me tell you what getting old actually feels like.",
      "Inside, I still feel twenty-five. The mirror is the only one who knows.",
      "You stop caring what people think. Honestly, it's the best part.",
      "You realise the small days were the big days. Tea in the morning. That's it.",
      "So don't fear getting old. Plenty of people never get the privilege."]),
    ("kindness", "The kindness they still remember 60 years later #shorts", "They never forgot this",
     "Five elders on the small kindnesses they never forgot.",
     ["kindness", "wholesome", "life lessons", "elders", "emotional"],
     ["I'm {age}. I've forgotten most of my achievements. I remember every kindness.",
      "A stranger paid my bus fare in nineteen sixty-two. I still think about her.",
      "Be kind to the person serving you. You have no idea what their morning was like.",
      "Say the compliment out loud. A kind thought nobody hears helps nobody.",
      "Be the person someone remembers fifty years from now. It costs nothing."]),
    ("money", "The best things they ever spent money on #shorts", "Best money they ever spent",
     "Five elders on the purchases that were worth every penny, and the ones that weren't.",
     ["spending", "money advice", "worth it", "life lessons", "elders"],
     ["I'm {age}. These are the best things I ever spent money on.",
      "A good bed and good shoes. If you're not in one, you're in the other.",
      "Travelling with my partner before our knees gave out. Worth every penny.",
      "Lessons for my kids. Swimming, music, languages. Nobody can take those away.",
      "And the worst? Anything I bought to impress people I didn't even like."]),
    ("family", "Parenting advice from grandparents of twelve #shorts", "Parents, hear this",
     "Five grandparents on what actually matters when raising children.",
     ["parenting", "grandparents", "family", "life lessons", "elders"],
     ["I'm {age}. Five children, twelve grandchildren. Here's what actually matters.",
      "Children don't remember what you bought them. They remember if you were there.",
      "Let them fail while the stakes are small. Rescue them less.",
      "Say sorry to your kids when you're wrong. It teaches more than being right.",
      "The days are long, but the years are short. Hold them while they still want you to."]),
    ("regret", "What fear cost them, in their own words #shorts", "What fear cost them",
     "Five elders on the chances fear made them skip.",
     ["fear", "courage", "regrets", "life lessons", "elders"],
     ["I'm {age}. I spent too many years afraid. Here's what fear cost me.",
      "I never sang in front of anyone. I had a good voice. Nobody will ever know.",
      "I turned down a job abroad because I was scared. I've wondered every year since.",
      "Most of what I worried about never happened. The worrying happened every day.",
      "Courage isn't feeling brave. It's being scared and doing it anyway. Start small."]),
    ("work", "What nobody tells you about retirement #shorts", "Retirement isn't what you think",
     "Five retirees on what they wish they'd known before they stopped working.",
     ["retirement", "purpose", "work", "life lessons", "elders"],
     ["I'm {age}. Retired twenty years. Here's what nobody tells you about retiring.",
      "Your job becomes your identity. When it ends, you need to know who you are without it.",
      "Build a life outside work now. Hobbies, friends, something that's only yours.",
      "Retiring with money but no purpose is a quiet kind of sad.",
      "So find work you'd do for free. Then find someone to pay you for it."]),
    ("peace", "How 90-year-olds found peace of mind #shorts", "The shortcut to peace of mind",
     "Five elders on letting go of worry.",
     ["peace of mind", "anxiety", "mindset", "life lessons", "elders"],
     ["I'm {age}. It took me sixty years to find peace. Here's the shortcut.",
      "You can't control what happens. Only the next thing you do.",
      "Not every thought in your head is true. Let some of them walk past.",
      "Get outside every morning. Sunlight on your face before your phone in your hand.",
      "Be gentle with yourself. You're the only one who's been with you the whole way."]),
    ("people", "How to spot good people, from 80-year-olds #shorts", "How to spot a good person",
     "Five elders on the signs of a genuinely good person.",
     ["good people", "red flags", "relationships", "life lessons", "elders"],
     ["I'm {age}. I've met a lot of people. Here's how to spot the good ones.",
      "Watch how they talk about the people who aren't in the room.",
      "Good people are happy for you. Really happy. Not quietly competing.",
      "Watch what they do when they lose. That's who they really are.",
      "And be that person yourself. You attract what you are."]),
    ("money", "What growing up poor taught them about money #shorts", "Grew up with nothing. Lessons.",
     "Five elders who grew up with very little on what it taught them.",
     ["frugal living", "growing up poor", "money", "life lessons", "elders"],
     ["I'm {age}. I grew up with nothing. Here's what that taught me about money.",
      "Cook at home. We ate like kings on what people now spend on one takeaway.",
      "Fix things before you replace them. My father's toolbox outlived three cars.",
      "Never be ashamed of where you started. Be ashamed of forgetting it.",
      "Rich is having enough. I learned that the day I stopped wanting more."]),
    ("love", "Marriage mistakes they'd never make again #shorts", "Marriage mistakes to avoid",
     "Five elders on the relationship mistakes they learned the hard way.",
     ["marriage advice", "relationship mistakes", "love", "life lessons", "elders"],
     ["I'm {age}. Divorced once, happily married once. I know the difference now.",
      "I kept score. Who did the dishes, who said sorry first. Keeping score kills love.",
      "Don't complain about your partner to your friends. Talk to your partner.",
      "Keep dating each other. Thursday nights for forty years. We never missed one.",
      "Love rarely dies in one big storm. It drips away. So do small things, every day."]),
    ("regret", "Advice for your 20s from people in their 80s #shorts", "If you're in your 20s, watch",
     "Five elders on what they'd want every twenty-something to hear.",
     ["20s", "young adults", "advice", "life lessons", "elders"],
     ["I'm {age}. If you're in your twenties, here's what I want you to hear.",
      "Your twenties are for collecting experiences, not things. Be broke somewhere beautiful.",
      "Don't marry out of fear of being alone. Lonely and married is the loneliest place.",
      "Save a little, even tiny amounts. Future you is a real person. Be kind to them.",
      "And call your grandparents. We have stories you'll wish you'd heard."]),
    ("work", "What 40 years of managing people taught them #shorts", "Every boss needs to hear this",
     "Five elders who led teams for decades on what makes people follow you.",
     ["leadership", "management", "boss", "life lessons", "elders"],
     ["I'm {age}. I managed hundreds of people. These lessons took me forty years.",
      "Praise in public. Correct in private. Never the other way round.",
      "People rarely quit jobs. They quit the person they report to.",
      "Admit when you don't know. People trust a leader who can say that.",
      "Remember birthdays. Remember their children's names. Small things build loyalty."]),
    ("health", "What they'd tell their 25-year-old body #shorts", "Dear 25-year-old me...",
     "Five elders on what they'd tell their younger body.",
     ["health tips", "aging", "self care", "life lessons", "elders"],
     ["I'm {age}. Here's what I'd tell my body at twenty-five.",
      "Wear sunscreen. My face tells the story of every summer I ignored it.",
      "Do something to keep your legs strong. Strong legs keep you independent.",
      "Protect your hearing. I miss my granddaughter's whispers now.",
      "Drink water, go to bed, and stop smoking. Today. Not Monday. Today."]),
    ("meaning", "If they could give you only one lesson #shorts", "The one lesson that matters most",
     "Five elders, one question: if you could pass on just one lesson, what would it be?",
     ["meaning of life", "what matters", "life lessons", "elders", "emotional"],
     ["I'm {age}. If I could give you only one lesson, it would be this.",
      "At the end, nobody asks for their bank statement. They ask for their people.",
      "Every room I ever loved, it was the people in it, not the room.",
      "So hug longer. Stay for one more cup of tea. Say what you mean.",
      "Because one day, this ordinary Tuesday will be the good old days."]),
]

# delivery per position: (tone, gesture)
DELIVERY = [
    ("warmly, with a knowing half-smile", "settles in and looks straight into the lens"),
    ("calmly and firmly, like passing on a rule", "leans slightly toward the camera"),
    ("with gentle humour", "gives a small wry smile and a slight shake of the head"),
    ("earnestly, holding eye contact", "pauses, then speaks slowly"),
    ("softly and with quiet emotion, eyes glistening", "takes a breath and holds the gaze after the last word"),
]
CAMERA = ["slow push-in from medium to medium close-up", "static medium close-up, subtle handheld drift",
          "slow push-in on the face", "static medium shot, gentle handheld drift",
          "very slow push-in to a close-up, holding on the face at the end"]

STYLE = ("Vertical 9:16, hyper-realistic documentary portrait, shot on a 50mm lens, shallow depth of field, "
         "natural skin texture with real wrinkles and pores, soft natural light, cinematic colour grade")
AUDIO_TAIL = "No music. No subtitles, no captions, no text on screen."

MUSIC = ["soft piano", "warm acoustic guitar", "gentle strings", "soft piano", "ambient pads"]


def pick_elders(i):
    """5 different elders per episode, rotating so the hook elder changes every day."""
    return [ORDER[(i * 3 + k * 5) % 25] for k in range(5)]


def flow_prompt(eid, k, line):
    age, pron, look, loc, accent = ELDERS[eid]
    place, ambience = LOCATIONS[loc]
    tone, gesture = DELIVERY[k]
    Pron = pron.capitalize()
    return (f"{STYLE}. {look[0].upper() + look[1:]}. Setting: {place}. {Pron} {gesture}. Camera: {CAMERA[k]}. "
            f"{Pron} speaks {tone}, in {accent}, saying: \"{line}\" "
            f"Ambient sound: {ambience}. {AUDIO_TAIL}")


def build():
    eps = []
    for i, (theme, title, hook, desc, tags, lines) in enumerate(EPISODES):
        n = i + 1
        cast = pick_elders(i)
        shots = []
        for k, (eid, line) in enumerate(zip(cast, lines)):
            age, pron, look, loc, accent = ELDERS[eid]
            line = line.replace("{age}", age_words(age).capitalize() if line.startswith("{age}") else age_words(age))
            tone, gesture = DELIVERY[k]
            shots.append({
                "n": k + 1, "dur": 8, "loc": loc, "chars": [eid],
                "keyframe": f"{look}, looking into the lens. Setting: {LOCATIONS[loc][0]}",
                "action": gesture, "camera": CAMERA[k],
                "lines": [{"c": eid, "t": line, "tone": tone}],
                "sfx": LOCATIONS[loc][1],
                "flow_prompt": flow_prompt(eid, k, line),
            })
        eps.append({
            "id": f"ELD-{n:03d}", "number": n, "theme": theme,
            "title": title, "logline": f"{theme.capitalize()}: {desc}",
            "hook_text": hook,
            "description": desc + " New lesson every day. Which one hit hardest? Tell us below.",
            "tags": tags + ["ask the elders", "advice", "wisdom", "shorts"],
            "music": MUSIC[i % len(MUSIC)],
            "shots": shots,
            "loop_note": "the last line lands on a held close-up; the next Short opens on a new face",
        })
    return eps


def bible():
    return {
        "channel_id": "elders",
        "show_title": "Ask The Elders",
        "tagline": "Life lessons from people who've lived it. One theme, five voices, 40 seconds.",
        "audience": "general (16+), NOT made for kids",
        "format": "One theme per Short. Five different elders (70-95), one hard-earned lesson each, 8 s per clip, spoken to camera.",
        "source": "flow",
        "episode_id_prefix": "ELD",
        "target_seconds": [36, 44],
        "max_seconds": 90,
        "style_prompt": STYLE,
        "audio_prompt": AUDIO_TAIL,
        "negative_prompt": "text, subtitles, watermarks added by us, logos, celebrities, real identifiable people, uniforms of real organisations",
        "characters": {eid: {"name": f"Elder {eid[1:]}", "age": a, "ref_prompt": look, "home_location": loc,
                             "voice": accent, "tts_voice_id": ""}
                       for eid, (a, p, look, loc, accent) in ELDERS.items()},
        "locations": {k: v[0] for k, v in LOCATIONS.items()},
        "themes": ["money", "love", "regret", "work", "health", "friendship", "family", "kindness", "peace", "people", "aging", "meaning"],
        "content_rules": [
            "Characters are AI-generated; never name them, never claim they are real people or real interviews.",
            "Universal life lessons only. No specific investments, products, medical treatments, legal advice or politics.",
            "Line 1 always states the elder's age and promises the theme. Line 5 is the emotional closer.",
            "Each line <= 18 words so Veo can say it naturally in 8 s.",
            "No famous quotes attributed to anyone; write original lines.",
        ],
        "music_moods": ["soft piano", "warm acoustic guitar", "gentle strings", "ambient pads"],
        "made_for_kids": False,
        "youtube_category": "22",
        "nonverbal": False,
        "ai_disclosure": "The people in this video are AI-generated characters (Google Veo). The lessons are real-world wisdom.",
        "overlays": {"hook": True, "captions": True},
        "flow": {"model": "Veo 3.1 Lite", "aspect": "9:16", "outputs_per_prompt": 1, "clip_seconds": 8,
                 "credits_per_clip": 10, "daily_free_credits": 50},
        "compilation_title": "{show} | {label} - {n} Life Lessons Back to Back",
        "compilation_tags": ["life lessons", "elders", "wisdom", "advice"],
        "compilations": {"weekly": True, "monthly": True},
    }


if __name__ == "__main__":
    (CH / "episodes").mkdir(parents=True, exist_ok=True)
    (CH / "channel.json").write_text(json.dumps(bible(), indent=2, ensure_ascii=False) + "\n")
    eps = build()
    for a in (0, 15):
        f = CH / "episodes" / f"eps_{a + 1:03d}-{a + 15:03d}.json"
        f.write_text(json.dumps({"episodes": eps[a:a + 15]}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(eps)} episodes to {CH}")
