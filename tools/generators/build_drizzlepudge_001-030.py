import json, sys
from pathlib import Path

OUT = Path(sys.argv[1])
TAGS = ["cartoons for kids", "kids cartoon", "funny cartoon", "preschool", "toddler", "Drizzle and Pudge"]
JUMP_SFX = "big happy splash in slow motion, both giggle 'yay!', sparkly chime"


def S(n, dur, loc, chars, key, action, camera, sfx):
    return {"n": n, "dur": dur, "loc": loc, "chars": chars, "keyframe": key, "action": action,
            "camera": camera, "lines": [], "sfx": sfx}


def jump(n, loc, extra_chars=(), note=""):
    chars = ["drizzle", "pudge", *extra_chars]
    return S(n, 6, loc, chars,
             f"Drizzle drips a perfect round shiny puddle on the ground, Pudge crouching ready to jump{note}",
             "Pudge jumps into the puddle with both feet, water splashes up in a sparkly crown, everyone laughs and waves at the camera",
             "low wide angle, slow motion on the splash", JUMP_SFX)


def E(num, title, logline, hook, desc, extra_tags, music, shots, guests=None):
    ep = {"id": f"DP-{num:03d}", "number": num, "title": f"{title} | Drizzle & Pudge", "logline": logline,
          "hook_text": hook, "description": desc + " A wordless cartoon for little ones, new episode every day.",
          "tags": (extra_tags + TAGS)[:12], "music": music, "shots": shots,
          "loop_note": "ends on the Puddle Jump; loops to the opening"}
    if guests:
        ep["guests"] = guests
    return ep


eps = [
E(1, "Hiccup Bubbles! 🫧", "Drizzle's hiccups fill the meadow with bubbles, one floats Bitsy the ladybug up into the sky, and the friends gently bring her back down.",
  "Every hiccup makes BUBBLES!", "Drizzle hiccups bubbles and Bitsy floats away. Can Pudge help?", ["bubbles"], "playful xylophone", [
  S(1, 8, "meadow", ["drizzle", "pudge"], "Drizzle floating happily above Pudge in the sunny meadow, both smiling", "Drizzle hiccups and a stream of shiny bubbles pops out of her; Pudge claps and chases them", "medium wide, gentle follow", "'hic!' sounds, bubbles popping, Pudge giggles"),
  S(2, 8, "meadow", ["pudge", "bitsy"], "Pudge popping bubbles with one finger, Bitsy sitting on a daisy watching", "a big bubble drifts down over Bitsy and lifts her up into the air inside it, Bitsy waves her tiny arms", "close on Bitsy then tilt up", "soft whoosh, tiny surprised squeak, Pudge gasps 'uh-oh!'"),
  S(3, 8, "sky", ["drizzle", "bitsy"], "Bitsy's bubble floating high among fluffy clouds, Drizzle zooming up after it", "Drizzle catches up and cuddles the bubble gently in her cloud arms", "wide sky shot, Drizzle flying in", "whoosh, sweet 'ooh'"),
  S(4, 8, "meadow", ["drizzle", "pudge", "bitsy"], "Drizzle floating down slowly, Pudge holding out his paws below", "the bubble lands softly in Pudge's paws and pops, Bitsy is safe and hugs Pudge's nose", "medium shot", "soft pop, happy giggles, little buzz"),
  jump(5, "meadow")]),
E(2, "Too Sunny for Rain ☀️", "On a hot day Drizzle can't make rain for Pudge's thirsty flowers until Pudge makes her laugh so hard she pours.",
  "The flowers are thirsty!", "Pudge's flowers need water but Drizzle is all puffed out. A giggle saves the day!", ["laughing", "friendship"], "silly tuba", [
  S(1, 8, "gran_garden", ["pudge"], "Pudge looking sadly at a row of droopy flowers in the hot sun", "the flowers droop lower, Pudge fans them with his hat", "medium shot, heat shimmer", "buzzing bees, sad little 'awww'"),
  S(2, 8, "gran_garden", ["drizzle", "pudge"], "Drizzle squeezing her cheeks trying to rain, Pudge watching hopefully", "Drizzle squeezes, only one tiny drop falls, she sighs and goes flat", "two-shot", "straining 'mmmmm', single plip, deflating sound"),
  S(3, 8, "gran_garden", ["pudge", "drizzle"], "Pudge putting a flower pot on his head like a hat and pulling a funny face", "Pudge waddles like a penguin with the pot on his head; Drizzle starts to giggle", "medium shot", "silly boing steps, giggles building"),
  S(4, 8, "gran_garden", ["drizzle", "pudge"], "Drizzle laughing so hard she wobbles, rain pouring from her", "happy rain falls over the flowers, they stand up tall and bloom; Pudge dances in the rain", "wide shot", "rain shower, joyful laughter, flowers going 'pop pop pop'"),
  jump(5, "gran_garden")]),
E(3, "Rainbow Sneeze 🌈", "Drizzle sneezes colours that paint Pudge in rainbow stripes, so the friends use her colourful sneezes to paint a rainbow on Gran's fence.",
  "ACHOO! Rainbow everywhere!", "Drizzle's sneeze turns Pudge into a rainbow! Learn the colours of the rainbow with Drizzle & Pudge.", ["colors", "rainbow", "learn colors"], "playful xylophone", [
  S(1, 8, "gran_garden", ["drizzle", "pudge"], "Drizzle sniffing a big sunflower, nose twitching, Pudge standing next to her", "Drizzle's face scrunches up for a sneeze", "close two-shot", "sniff sniff, 'ah... ah...'"),
  S(2, 8, "gran_garden", ["drizzle", "pudge"], "Drizzle sneezing, a burst of red, orange, yellow, green, blue and purple drops flying out", "the colours splash onto Pudge, he is covered in rainbow stripes", "medium shot, colour burst", "'ACHOO!', paint splats"),
  S(3, 8, "pond_bank", ["pudge"], "Pudge on the grassy bank looking at his rainbow reflection in the pond", "Pudge looks surprised, then laughs and spins to see all his colours", "over-the-shoulder into the reflection", "gasp, giggle"),
  S(4, 10, "gran_garden", ["drizzle", "pudge", "gran_tortle"], "Gran Tortle pointing to her plain wooden fence, Drizzle and Pudge ready", "Drizzle sneezes one colour at a time onto the fence as Pudge points: red, orange, yellow, green, blue, purple, making a rainbow; Gran claps", "slow pan along the fence", "six cute sneezes each with a different chime note, Gran chuckles"),
  jump(5, "gran_garden", note=", now with rainbow-coloured water")]),
E(4, "Snow in Summer?! ❄️", "Drizzle shivers and snows a tiny snowman patch on a summer day; when it melts, the friends turn the meltwater into the best puddle ever.",
  "Snow... in SUMMER?", "A tiny snow surprise on a sunny day! Drizzle & Pudge learn that changes can be fun.", ["snowman", "summer"], "magic twinkle", [
  S(1, 8, "meadow", ["drizzle", "pudge"], "Drizzle shivering after flying through a cool breeze, Pudge looking up", "Drizzle shivers and soft snowflakes fall from her onto one small patch of grass", "medium wide", "brrr sound, tinkly snowflakes"),
  S(2, 8, "meadow", ["pudge"], "Pudge kneeling by a small patch of snow in the green summer meadow", "Pudge rolls a tiny snowman with a pebble face and a leaf scarf", "close shot", "crunchy snow, happy hums"),
  S(3, 8, "meadow", ["pudge", "drizzle"], "the tiny snowman starting to melt in the warm sun, Pudge's face falling", "the snowman slowly melts into water, Pudge looks a bit sad, Drizzle pats his head", "slow push-in on the snowman", "drip drip, gentle 'awww'"),
  S(4, 8, "meadow", ["drizzle", "pudge"], "Drizzle pointing at the melted water, an idea sparkle above her", "Drizzle adds rain to the melted snow making a big shiny puddle; Pudge smiles wide", "medium shot", "idea 'ding!', rain pitter-patter"),
  jump(5, "meadow")]),
E(5, "Fizz Took the Acorn! 🌰", "Cheeky Fizz snatches Pudge's shiny acorn, Drizzle's sad rain soaks Fizz, and Pudge's kindness with his umbrella makes Fizz share.",
  "Hey! That's Pudge's acorn!", "Fizz learns that sharing is more fun than grabbing. A story about kindness.", ["sharing", "kindness"], "bouncy ukulele", [
  S(1, 8, "big_oak", ["pudge"], "Pudge proudly holding up a big shiny golden acorn under the oak tree", "Pudge polishes the acorn and admires it", "close shot", "sparkle chime, happy 'ooh'"),
  S(2, 6, "big_oak", ["fizz", "pudge"], "Fizz zooming past in a blur", "Fizz grabs the acorn and zips around the tree, Pudge spins dizzily", "whip pan", "zoom whoosh, cheeky squirrel giggle"),
  S(3, 8, "big_oak", ["drizzle", "fizz"], "Drizzle above Fizz looking sad, a little storm forming", "Drizzle's sad rain pours right on Fizz, who is soaked, his big tail drooping", "medium shot", "rain shower, sad sniffle, 'uh-oh'"),
  S(4, 10, "big_oak", ["pudge", "fizz"], "Pudge walking up to wet Fizz holding a big leaf like an umbrella", "Pudge holds the leaf umbrella over Fizz; Fizz looks at the acorn, then gives it back; Pudge breaks it into two and shares", "slow push-in", "soft music-box notes, happy giggles"),
  jump(5, "big_oak", ["fizz"], note=", Fizz watching")]),
E(6, "Where's Bitsy? 🐞", "Bitsy goes missing at dusk, so Drizzle rains glowing star-drops to light the hedge while Pudge counts the places they search.",
  "Bitsy is hiding! Can you spot her?", "Help Drizzle and Pudge find Bitsy! Count 1, 2, 3 along the way.", ["counting", "hide and seek"], "gentle music box", [
  S(1, 8, "meadow", ["pudge", "drizzle"], "evening meadow, Pudge looking around worried, Drizzle beside him", "Pudge looks under a leaf, behind a stone, shaking his head", "medium shot, warm dusk light", "crickets, little 'hmm?'"),
  S(2, 8, "meadow", ["drizzle"], "Drizzle glowing softly, tiny glowing star-shaped drops falling from her", "glowing star-drops light up a path through the flowers", "wide, magical glow", "magic twinkles"),
  S(3, 10, "meadow", ["pudge", "drizzle"], "Pudge holding up one finger beside a glowing mushroom", "Pudge checks one mushroom, two flowers, three leaves, holding up fingers each time", "tracking shot", "three soft chimes rising in pitch, 'one... two... three!' as chime tones only"),
  S(4, 8, "meadow", ["bitsy", "pudge"], "inside a closed daisy, Bitsy fast asleep, Pudge peeking in with a smile", "the daisy opens gently, Bitsy yawns and waves", "close up", "tiny yawn, 'awww'"),
  jump(5, "meadow", ["bitsy"], note=", Bitsy on Pudge's head, glowing puddle")]),
E(7, "Musical Raindrops 🎵", "Drizzle discovers her raindrops play notes on Gran's flower pots, and the friends put on a garden concert that makes Gran dance.",
  "Raindrops that play MUSIC!", "Plink, plonk, plunk! Drizzle's raindrops make music in Gran's garden.", ["music", "kids music"], "playful xylophone", [
  S(1, 8, "gran_garden", ["drizzle", "pudge"], "a row of different-sized flower pots, one raindrop falling from Drizzle onto a pot", "the drop hits the pot and plays a musical note; Drizzle and Pudge look at each other amazed", "close on pots then two-shot", "single bright xylophone 'plink'"),
  S(2, 8, "gran_garden", ["pudge"], "Pudge lining up the pots from biggest to smallest", "Pudge arranges the pots in a neat row", "top-down", "pots sliding, little hums"),
  S(3, 10, "gran_garden", ["drizzle", "pudge"], "Drizzle floating along the row of pots dripping on each", "Drizzle plays a happy tune across the pots, Pudge conducts with a twig", "tracking shot along the pots", "a cheerful simple melody of plinks"),
  S(4, 8, "gran_garden", ["gran_tortle", "pudge"], "Gran Tortle peeking from her shed, starting to tap her foot", "Gran does a slow happy twirl, Pudge dances with her", "medium shot", "melody continues, Gran chuckles"),
  jump(5, "gran_garden", note=", the splash plays a final musical note")]),
E(8, "Windy Day Whoosh 🌬️", "A big gust blows Drizzle away across the sky, and Pudge, Fizz and Gran use Gran's kite tail to gently pull her home.",
  "Hold on, Drizzle!", "When the wind blows Drizzle away, her friends work together to bring her home. Teamwork!", ["teamwork", "kite", "wind"], "bouncy ukulele", [
  S(1, 8, "meadow", ["drizzle", "pudge"], "Drizzle and Pudge playing on a breezy day, flowers bending", "a strong gust pushes Drizzle away across the sky, she spins and squeaks", "wide shot", "whoosh of wind, 'eeek!'"),
  S(2, 8, "gran_garden", ["pudge", "gran_tortle"], "Pudge running to Gran, pointing at the sky", "Gran pulls out a colourful kite with a long ribbon tail from her shed", "medium shot", "running footsteps, idea 'ding!'"),
  S(3, 10, "meadow", ["fizz", "pudge"], "the kite flying high, Pudge and Fizz holding the string together on the ground", "the kite's ribbon tail floats up to Drizzle, she grabs it", "low angle looking up", "flapping kite, hopeful 'ooh'"),
  S(4, 8, "meadow", ["gran_tortle", "drizzle"], "Gran, Pudge and Fizz pulling the string in a line like tug of war", "they gently reel Drizzle down until she lands in a hug", "wide, then hug close up", "heave-ho grunts, happy cheer"),
  jump(5, "meadow", ["fizz"])]),
E(9, "The Sandcastle Splash 🏰", "Drizzle's hiccup washes away Pudge's sandcastle at the pond bank, so the friends try again and build a bigger, stronger one together.",
  "Oops! The sandcastle!", "When things go wrong, try again together! Drizzle & Pudge build a sandcastle.", ["try again", "sandcastle"], "silly tuba", [
  S(1, 8, "pond_bank", ["pudge"], "Pudge proudly finishing a small sandcastle on the sandy grass edge with a flower flag", "Pudge places the flower flag on top and smiles", "close shot", "patting sand, proud hum"),
  S(2, 6, "pond_bank", ["drizzle", "pudge"], "Drizzle floating over the sandcastle about to hiccup", "Drizzle hiccups a splash of rain and the sandcastle melts down", "medium shot", "'hic!', splash, sad trombone"),
  S(3, 8, "pond_bank", ["drizzle", "pudge"], "Drizzle covering her face sorry, Pudge looking at the mushy sand", "Drizzle gives a sorry little hug; Pudge smiles and picks up his bucket again", "two-shot", "soft 'sorry' coo, gentle music"),
  S(4, 10, "pond_bank", ["fizz", "pudge"], "Pudge, Fizz and Drizzle building together", "Drizzle sprinkles just a little water to make the sand sticky, Fizz digs, Pudge stacks; a tall castle rises", "time-lapse style building", "building sounds, cheerful hums"),
  jump(5, "pond_bank", ["fizz"], note=", the big castle standing proudly behind them")]),
E(10, "Bedtime Stars 🌙", "Drizzle can't fall asleep, so Pudge counts sheep-shaped clouds with her until she rains soft glowing stars and they both drift off.",
  "Time for sleep, Drizzle 🌙", "A calm bedtime cartoon. Count the sleepy sheep clouds with Drizzle and Pudge.", ["bedtime", "lullaby", "sleep"], "gentle music box", [
  S(1, 8, "pudge_burrow", ["drizzle", "pudge"], "Pudge in pyjamas in his cosy bed, Drizzle floating wide awake by the round window", "Drizzle bounces around restlessly, Pudge yawns", "medium shot, warm lantern light", "soft yawn, gentle bouncy sounds"),
  S(2, 10, "night_meadow", ["drizzle", "pudge"], "view through the window of fluffy clouds shaped like sheep floating over the moon", "Pudge points at each sheep cloud as it hops over the moon, one, two, three", "slow pan across the sky", "three soft bell tones, crickets"),
  S(3, 8, "pudge_burrow", ["drizzle"], "Drizzle's eyes getting heavy, small glowing stars drifting down from her", "glowing stars float softly around the room", "slow push-in", "magic twinkle, soft yawn"),
  S(4, 8, "pudge_burrow", ["drizzle", "pudge"], "Drizzle curled up on Pudge's pillow, both asleep, stars glowing on the ceiling", "the lantern dims gently, a tiny smile on both faces", "slow pull back", "gentle breathing, lullaby hum"),
  S(5, 6, "pudge_burrow", ["drizzle", "pudge"], "morning sunlight through the round window, both waking and stretching", "Drizzle drips a tiny puddle on the floor and Pudge does a sleepy little hop into it", "medium shot", "tiny splash, morning birdsong, giggles")]),
E(11, "Bouncy Bubble Puddle 🫧", "Drizzle rains a magic bubble puddle that's bouncy like a trampoline, and even slow Gran Tortle has a turn.",
  "A BOUNCY puddle?!", "Boing boing! Drizzle makes a magic bouncy puddle for everyone to share.", ["bouncy", "taking turns"], "bouncy ukulele", [
  S(1, 8, "puddle_lane", ["drizzle", "pudge"], "Drizzle raining shimmering bubbly drops into a puddle that glows", "Pudge pokes the puddle with his boot and it wobbles like jelly", "close on puddle", "bubbly rain, wobble 'boing'"),
  S(2, 8, "puddle_lane", ["pudge"], "Pudge standing on the shiny wobbly puddle", "Pudge bounces gently up and down, giggling, just a little off the ground", "low angle", "boing boing, giggles"),
  S(3, 8, "puddle_lane", ["fizz", "pudge"], "Fizz running up wanting a turn, Pudge stepping off", "Pudge waves Fizz on to take a turn; Fizz bounces and does a happy spin", "medium shot", "boing, cheeky squeak"),
  S(4, 10, "puddle_lane", ["gran_tortle", "pudge"], "Gran Tortle stepping carefully onto the puddle holding Pudge's paw", "Gran bounces very slowly and gently, then laughs with delight", "medium shot", "slow 'boooing', warm chuckle"),
  jump(5, "puddle_lane", note=", the puddle gives one last tiny boing")]),
E(12, "The Hiccup Cure 😄", "The friends try every silly trick to stop Drizzle's hiccups until Bitsy's tickle works, and then Pudge catches the hiccups.",
  "How do you stop HICCUPS?", "Drizzle has the hiccups! Which silly trick will work?", ["hiccups", "funny"], "silly tuba", [
  S(1, 8, "meadow", ["drizzle", "pudge"], "Drizzle hiccuping, each hiccup popping out a little flower petal", "petals pop out with each hiccup, Pudge scratches his head", "medium shot", "'hic! hic!', petal poofs"),
  S(2, 8, "meadow", ["pudge", "drizzle"], "Pudge making a big funny 'boo' face", "Pudge pops up with a silly face; Drizzle laughs but hiccups again", "two-shot", "playful 'boo!' noise, laugh, 'hic!'"),
  S(3, 8, "meadow", ["drizzle", "pudge"], "Drizzle floating upside down holding her breath, cheeks puffed", "Drizzle turns pink holding her breath, then hiccups and spins", "medium shot", "'mmmm', 'hic!', spin whoosh"),
  S(4, 8, "meadow", ["bitsy", "drizzle"], "tiny Bitsy landing on Drizzle's fluffy side", "Bitsy tickles Drizzle, who giggles so much the hiccups stop; then Pudge hiccups a bubble", "close up then two-shot", "tickle giggles, silence, then Pudge's 'hic!'"),
  jump(5, "meadow", note=", Pudge still hiccuping cutely")]),
E(13, "Painting Gran's Fence 🎨", "Drizzle's colour rain helps paint Gran's fence until Fizz smudges it, and Fizz says sorry by painting a heart.",
  "Who smudged the paint?", "A colourful cartoon about saying sorry. Drizzle, Pudge and Fizz paint Gran's fence.", ["painting", "saying sorry", "colors"], "playful xylophone", [
  S(1, 8, "gran_garden", ["gran_tortle", "drizzle"], "Gran holding a paintbrush by her plain fence, Drizzle eager to help", "Drizzle rains soft blue paint drops that paint a sky across the fence", "wide on the fence", "pitter-patter paint, Gran's happy hum"),
  S(2, 8, "gran_garden", ["pudge"], "Pudge painting green grass with a big brush", "Pudge paints big swooshes of grass, gets a dot of paint on his nose", "medium shot", "brush swooshes, giggle"),
  S(3, 6, "gran_garden", ["fizz"], "Fizz zooming past the wet fence", "Fizz's fluffy tail smears a long streak through the paint", "whip pan", "zoom, smudge squelch, everyone gasps"),
  S(4, 10, "gran_garden", ["fizz", "gran_tortle"], "Fizz looking sorry, ears down, holding his paint-covered tail", "Fizz uses his tail like a brush to paint a big red heart over the smudge; Gran hugs him", "slow push-in", "soft music box, happy 'awww'"),
  jump(5, "gran_garden", ["fizz"], note=", the painted fence behind them")]),
E(14, "Feathers for a Baby Bird 🐣", "Drizzle rains soft feathers that Pudge turns into a cosy nest for a lost baby bird until its mama returns.",
  "A baby bird needs help!", "Drizzle and Pudge help a lost baby bird. A gentle story about helping others.", ["helping", "baby bird", "animals"], "gentle music box", [
  S(1, 8, "big_oak", ["pudge", "baby_bird"], "a tiny fluffy baby bird sitting alone on a mossy root, Pudge kneeling to look", "the baby bird peeps sadly; Pudge looks around for its mama", "close shot", "tiny sad peeps"),
  S(2, 8, "big_oak", ["drizzle"], "Drizzle above them, eyes sparkling with an idea", "soft white feathers rain down from Drizzle", "medium shot", "gentle whoosh, magic twinkle"),
  S(3, 8, "big_oak", ["pudge", "baby_bird"], "Pudge gathering feathers into a round cosy nest on a low mossy root", "Pudge places the baby bird in the nest, it snuggles in and smiles", "close shot", "soft rustle, happy cheep"),
  S(4, 8, "big_oak", ["mama_bird", "baby_bird"], "a mama bird swooping down to the nest", "mama bird hugs the baby with her wings and bows thank you to Pudge", "medium shot", "happy chirping duet"),
  jump(5, "big_oak", note=", the birds singing on a branch above")],
  guests={"baby_bird": {"name": "Baby Bird", "ref_prompt": "a tiny round fluffy baby bluebird chick with big eyes and tiny wings", "voice": "tiny peeps"},
          "mama_bird": {"name": "Mama Bird", "ref_prompt": "a kind round bluebird mother with soft blue feathers and a gentle smile", "voice": "sweet chirps"}}),
E(15, "Upside-Down Rain ⬆️", "Drizzle's rain falls upward one silly morning, floating Pudge's hat and Bitsy into the air, until a big sneeze sets everything right.",
  "The rain is going UP?!", "A silly upside-down day with Drizzle and Pudge!", ["silly", "upside down"], "magic twinkle", [
  S(1, 8, "puddle_lane", ["drizzle", "pudge"], "Drizzle raining, but the raindrops float upward from the ground into the sky", "Pudge watches the drops rise, his eyes wide", "low angle looking up", "reverse plinks, 'ooh?'"),
  S(2, 8, "puddle_lane", ["pudge"], "Pudge's raincoat hood and hat floating off his head upward", "Pudge hops to grab his hat as it floats away gently", "medium shot", "floaty whoosh, giggle"),
  S(3, 8, "puddle_lane", ["bitsy", "pudge"], "Bitsy floating upward with a raindrop, spinning happily", "Bitsy does somersaults in the air, Pudge laughs", "close up", "tiny happy buzz"),
  S(4, 8, "puddle_lane", ["drizzle", "pudge"], "Drizzle's nose twitching", "Drizzle sneezes and everything gently falls back down: the hat lands on Pudge's head, Bitsy lands on his nose", "two-shot", "'achoo!', soft landing plops"),
  jump(5, "puddle_lane")]),
E(16, "Shadow Puppets 🦋", "On a cloudy evening Drizzle glows so Pudge can make shadow puppets, and a giant scary shadow turns out to be tiny Bitsy.",
  "Whose BIG shadow is that?", "Shadow puppet fun with Drizzle and Pudge. Nothing to be scared of!", ["shadow puppets", "brave"], "gentle music box", [
  S(1, 8, "pudge_burrow", ["drizzle", "pudge"], "Drizzle glowing like a soft lamp, Pudge in front of a plain wall", "Pudge makes a bunny shadow with his paws on the wall", "wide on the wall", "soft glow hum, giggle"),
  S(2, 8, "pudge_burrow", ["fizz", "pudge"], "Fizz joining, making a butterfly shadow with his tail", "the shadow butterfly flutters across the wall", "wide on the wall", "playful flutter sounds"),
  S(3, 8, "pudge_burrow", ["pudge", "fizz"], "a huge round shadow with antennae appearing on the wall", "Pudge and Fizz hug each other wide-eyed", "slow push-in on the shadow", "soft 'uh-oh', gentle suspense note"),
  S(4, 8, "pudge_burrow", ["bitsy", "drizzle"], "tiny Bitsy sitting right in front of Drizzle's glow, waving", "Bitsy waves, the giant shadow waves too; everyone laughs", "reveal pan", "tiny buzz, big relieved laugh"),
  jump(5, "pudge_burrow", ["fizz"], note=" on the burrow floor")]),
E(17, "The Biggest Splash 💦", "Pudge and Fizz have a splash contest, Fizz wins and Pudge cheers for him, so Drizzle makes one giant puddle for both to share.",
  "Who makes the biggest splash?", "A splash contest with a happy ending. Good sports cheer for each other!", ["good sport", "splash"], "bouncy ukulele", [
  S(1, 8, "puddle_lane", ["pudge", "fizz"], "Pudge and Fizz standing at two puddles, ready like athletes", "they bump fists and get ready to jump", "low wide angle", "drumroll"),
  S(2, 8, "puddle_lane", ["pudge"], "Pudge jumping into his puddle", "a nice medium splash", "slow motion", "splash, 'yay'"),
  S(3, 8, "puddle_lane", ["fizz", "pudge"], "Fizz jumping and spinning into his puddle with his big tail", "a huge tail-powered splash; Pudge cheers and claps for Fizz", "slow motion then two-shot", "huge splash, cheering"),
  S(4, 8, "puddle_lane", ["drizzle", "fizz"], "Drizzle smiling above both of them", "Drizzle rains a giant puddle big enough for both", "high angle", "magic twinkle, rain whoosh"),
  jump(5, "puddle_lane", ["fizz"], note=", Fizz and Pudge holding hands")]),
E(18, "The Lost Red Boot 👢", "Pudge loses a red rain boot and follows footprints to find a frog using it as a boat, so he lets the frog keep it.",
  "Where did Pudge's boot go?", "Follow the footprints! Pudge finds his boot and makes a new friend.", ["lost and found", "frog", "sharing"], "playful xylophone", [
  S(1, 8, "puddle_lane", ["pudge"], "Pudge hopping on one foot with one red boot, the other foot bare", "Pudge looks around confused, wiggling his bare toes", "medium shot", "hop hop, 'hmm?'"),
  S(2, 8, "puddle_lane", ["pudge", "drizzle"], "little wet webbed footprints leading along the path", "Pudge and Drizzle follow the footprints, tiptoeing", "tracking shot", "tiptoe music, plip plip"),
  S(3, 8, "pond_bank", ["frog", "pudge"], "a small happy frog floating in Pudge's red boot like a little boat at the pond's edge", "the frog paddles happily; Pudge watches from the grass", "medium shot", "ribbit, giggle"),
  S(4, 8, "pond_bank", ["pudge", "drizzle"], "Pudge waving to the frog, Drizzle raining a big leaf down onto Pudge's bare foot", "Pudge wears the leaf like a funny shoe and laughs", "two-shot", "leaf rustle, laughter, happy ribbit"),
  jump(5, "pond_bank", note=", the frog jumping in too")],
  guests={"frog": {"name": "Frog", "ref_prompt": "a small round bright green baby frog with big friendly eyes and a wide smile", "voice": "happy ribbits"}}),
E(19, "Rumble the Grumpy Cloud ⛈️", "A big grumpy thundercloud blocks the sun, Drizzle gives him a hug, and he rains a rainbow and becomes a new friend.",
  "Why is Rumble so grumpy?", "Even grumpy clouds need a hug. A kindness cartoon with Drizzle & Pudge.", ["kindness", "feelings", "rainbow"], "magic twinkle", [
  S(1, 8, "meadow", ["rumble", "pudge"], "a big round grey cloud with a pouty frown floating over the meadow, blocking the sun", "Rumble grumbles and the meadow gets shady; Pudge looks up", "low wide angle", "low cute grumble (not scary)"),
  S(2, 8, "sky", ["drizzle", "rumble"], "tiny Drizzle floating up to big Rumble", "Drizzle waves hello; Rumble turns away with a 'hmph'", "two-shot in the sky", "'hmph', little 'hi!'"),
  S(3, 8, "sky", ["drizzle", "rumble"], "Drizzle giving Rumble a big cloud hug", "Rumble's frown wobbles and turns into a shy smile", "slow push-in", "soft music box, warm 'awww'"),
  S(4, 8, "meadow", ["rumble", "pudge"], "Rumble happily raining a big bright rainbow over the meadow", "the sun shines through, Pudge dances under the rainbow", "wide", "joyful chime, laughter"),
  jump(5, "meadow", note=", Rumble smiling in the sky")],
  guests={"rumble": {"name": "Rumble", "ref_prompt": "a big round fluffy grey storm cloud character with a cute pouty face, small eyebrows, soft and not scary", "voice": "low cute grumbles"}}),
E(20, "Pudge's Birthday Surprise 🎉", "The friends plan a surprise party for Pudge, Drizzle accidentally rains confetti too early, and everyone laughs and celebrates anyway.",
  "SURPRISE... too early! 🎉", "Happy birthday, Pudge! A surprise that didn't quite go to plan.", ["birthday", "party", "surprise"], "bouncy ukulele", [
  S(1, 8, "big_oak", ["gran_tortle", "fizz"], "Gran and Fizz hanging bunting and balloons on the oak tree, whispering 'shh'", "they hide behind roots as footsteps come", "medium wide", "'shhh', tiptoes"),
  S(2, 8, "big_oak", ["drizzle"], "Drizzle hiding behind a branch, too excited, wobbling", "Drizzle can't hold it in and rains a burst of confetti early", "close shot", "excited squeal, confetti pop"),
  S(3, 8, "big_oak", ["pudge"], "Pudge arriving and stopping under the confetti still falling", "Pudge looks up at the confetti, then spots everyone hiding", "medium shot", "confetti swish, 'ooh?'"),
  S(4, 10, "big_oak", ["pudge", "gran_tortle"], "everyone jumping out with a cake with one candle, Pudge laughing", "Pudge laughs and hugs Drizzle; Gran holds the cake, everyone celebrates", "wide", "cheering, happy birthday melody on xylophone"),
  jump(5, "big_oak", ["fizz"], note=", wearing party hats")]),
E(21, "Bubble Bath Burrow 🛁", "Bath time turns into a bubble flood when Drizzle helps too much, so the friends tidy up together and have fun doing it.",
  "Too many BUBBLES!", "Bath time and tidy-up time with Drizzle and Pudge!", ["bath time", "tidy up"], "playful xylophone", [
  S(1, 8, "pudge_burrow", ["pudge"], "Pudge in a little wooden tub with a rubber boat", "Pudge splashes happily", "medium shot", "splashing, humming"),
  S(2, 8, "pudge_burrow", ["drizzle", "pudge"], "Drizzle raining bubbles into the tub", "bubbles grow and grow, filling the whole room", "wide shot", "bubbly whoosh, giggles"),
  S(3, 8, "pudge_burrow", ["gran_tortle"], "Gran opening the round door and getting covered in bubbles", "Gran laughs with a bubble beard", "medium shot", "door creak, poof, warm laugh"),
  S(4, 8, "pudge_burrow", ["pudge", "drizzle"], "Pudge in pyjamas mopping, Drizzle blowing bubbles out the window", "they tidy up together, the room sparkles clean", "time-lapse style", "tidy-up music, sparkle chime"),
  jump(5, "pudge_burrow", note=" in the clean burrow, one tiny puddle")]),
E(22, "Just Enough Rain 🌱", "Drizzle learns to give each of Gran's five little plants just the right amount of rain, counting one to five.",
  "Count the plants with Drizzle!", "Learn to count to 5 while Drizzle waters Gran's plants just right.", ["counting", "count to 5", "learning"], "playful xylophone", [
  S(1, 8, "gran_garden", ["drizzle", "gran_tortle"], "Drizzle pouring too much rain on one plant, making a mini flood; Gran chuckling", "the plant gets a big splash and bends; Drizzle covers her mouth", "medium shot", "big splash, 'oops!'"),
  S(2, 8, "gran_garden", ["gran_tortle", "drizzle"], "Gran showing a tiny gentle sprinkle from her watering can", "Gran sprinkles softly; Drizzle watches carefully and nods", "two-shot", "gentle sprinkle, 'ohhh'"),
  S(3, 10, "gran_garden", ["drizzle", "pudge"], "five little plants in pots in a row, Pudge holding up fingers", "Drizzle gives each plant a gentle sprinkle as Pudge counts with his fingers; each plant pops a flower", "tracking shot along the pots", "five rising chime notes with each flower pop"),
  S(4, 8, "gran_garden", ["gran_tortle", "drizzle"], "five blooming plants, Gran giving Drizzle a gold star sticker", "Drizzle glows proudly", "medium shot", "proud 'yay!', sparkle"),
  jump(5, "gran_garden")]),
E(23, "Leaf Pile Surprise 🍂", "Drizzle rains autumn leaves, the friends build a huge leaf pile, and Fizz pops out of it with a surprise.",
  "Who's hiding in the leaves?", "Autumn fun! Drizzle rains leaves for the biggest leaf pile ever.", ["autumn", "leaves", "fall"], "happy whistle", [
  S(1, 8, "meadow", ["drizzle", "pudge"], "Drizzle raining orange, red and yellow leaves that spin gently down", "Pudge spins around catching leaves", "wide shot", "rustling, happy whistle"),
  S(2, 8, "meadow", ["pudge", "gran_tortle"], "Pudge and Gran raking leaves into a big soft pile", "the pile grows taller than Pudge", "medium shot", "raking swish"),
  S(3, 8, "meadow", ["pudge"], "Pudge flopping backwards onto the soft leaf pile on the ground", "leaves fly up, Pudge giggles", "slow motion", "crunchy poof, giggles"),
  S(4, 8, "meadow", ["fizz", "pudge"], "Fizz popping out of the leaf pile holding an acorn crown", "Fizz places the acorn crown on Pudge's head", "close up", "pop!, surprised laugh"),
  jump(5, "meadow", ["fizz"], note=", leaves floating around")]),
E(24, "Firefly Friends ✨", "A little firefly can't find its friends, so Drizzle glows to guide it home and Pudge counts the fireflies as they gather.",
  "Count the fireflies! ✨", "Help a little firefly find its friends and count to five!", ["counting", "fireflies", "night"], "gentle music box", [
  S(1, 8, "night_meadow", ["pudge", "firefly"], "a tiny firefly with a dim glow alone on a flower at night, Pudge kneeling", "the firefly blinks sadly", "close shot", "crickets, tiny sigh"),
  S(2, 8, "night_meadow", ["drizzle", "firefly"], "Drizzle glowing softly beside the firefly", "the firefly's glow gets brighter next to Drizzle", "two-shot", "soft hum, twinkle"),
  S(3, 10, "night_meadow", ["pudge", "drizzle"], "fireflies appearing one by one across the meadow", "Pudge counts them on his fingers: one, two, three, four, five", "slow pan", "five soft twinkle notes"),
  S(4, 8, "night_meadow", ["firefly", "pudge"], "the little firefly joining its friends in a glowing circle", "the fireflies dance around Pudge in a happy ring", "wide magical shot", "happy twinkling melody"),
  jump(5, "night_meadow", note=", the puddle reflecting the moon and fireflies")],
  guests={"firefly": {"name": "Little Firefly", "ref_prompt": "a tiny cute firefly with a round glowing yellow tail, big eyes and tiny wings", "voice": "tiny happy hums"}}),
E(25, "Shapes in the Pond ⭐", "Drizzle's raindrops make ripples on the pond in the shape of a circle, a star and a heart as the friends watch from the bank.",
  "Can you name the shapes?", "Circle, star, heart! Learn shapes with Drizzle's magic raindrops.", ["shapes", "learn shapes", "learning"], "magic twinkle", [
  S(1, 8, "pond_bank", ["drizzle", "pudge"], "Pudge sitting safely on the grassy bank, Drizzle floating over the calm pond", "one drop makes a perfect circle ripple", "high angle over the pond", "plink, gentle chime"),
  S(2, 8, "pond_bank", ["drizzle"], "Drizzle concentrating, tongue out", "a pattern of drops makes a star-shaped ripple on the water", "high angle", "five little plinks, twinkle"),
  S(3, 8, "pond_bank", ["drizzle", "pudge"], "Drizzle making a heart ripple, Pudge clapping", "a heart-shaped ripple spreads across the pond", "high angle then reaction", "soft music box, 'ooh!'"),
  S(4, 8, "pond_bank", ["frog", "pudge"], "a happy frog on a lily pad jumping and making its own circle ripple", "the frog's splash makes a circle; Pudge and the frog laugh", "medium shot", "ribbit, splash, giggles"),
  jump(5, "pond_bank", note=" on the grass by the pond")],
  guests={"frog": {"name": "Frog", "ref_prompt": "a small round bright green baby frog with big friendly eyes and a wide smile", "voice": "happy ribbits"}}),
E(26, "Cloud Umbrella Picnic 🧺", "On a very hot picnic day Drizzle turns herself into a shady cloud umbrella so everyone can enjoy the picnic together.",
  "Too hot for a picnic?", "Drizzle becomes a cloud umbrella so everyone can share the picnic.", ["picnic", "summer", "sharing"], "happy whistle", [
  S(1, 8, "picnic_hill", ["pudge", "gran_tortle"], "a checked picnic blanket on the hill, Pudge and Gran fanning themselves in the hot sun", "the sun beams hot, Gran wipes her brow", "wide shot, heat shimmer", "buzzing summer, tired sigh"),
  S(2, 8, "picnic_hill", ["drizzle"], "Drizzle puffing herself up bigger and wider", "Drizzle stretches into a big flat cloud shape", "low angle", "stretchy 'mmmmm', puff"),
  S(3, 8, "picnic_hill", ["drizzle", "pudge"], "Drizzle hovering over the blanket like an umbrella making cool shade", "everyone sighs happily in the shade", "wide shot", "cool breeze, relieved 'ahhh'"),
  S(4, 8, "picnic_hill", ["fizz", "gran_tortle"], "Fizz sharing berries from his basket with Gran and Pudge", "everyone shares the picnic, little ants carry away one crumb", "medium shot", "happy munching, tiny ant march music"),
  jump(5, "picnic_hill", ["fizz"])]),
E(27, "A Snowman for Drizzle ☃️", "On the first snowy day Drizzle feels left out because she can't hold snow, so her friends build a snow-Drizzle just for her.",
  "First snow day! ❄️", "A heart-warming winter cartoon about including everyone.", ["snow day", "winter", "friendship"], "gentle music box", [
  S(1, 8, "snowy_hill", ["drizzle", "pudge"], "Drizzle snowing gently over the meadow, Pudge in a woolly hat catching flakes on his tongue", "Pudge spins happily in the snow", "wide shot", "soft snow sounds, giggles"),
  S(2, 8, "snowy_hill", ["pudge", "fizz"], "Pudge and Fizz rolling big snowballs", "they stack the snowballs together", "medium shot", "crunchy snow, effort grunts"),
  S(3, 8, "snowy_hill", ["drizzle"], "Drizzle watching from above, a little sad because her cloud arms can't hold snow", "a small sad sigh, one snowflake falls", "slow push-in", "soft sad note"),
  S(4, 10, "snowy_hill", ["pudge", "drizzle"], "Pudge revealing a round fluffy snow sculpture shaped exactly like Drizzle with pebble eyes", "Drizzle gasps and hugs her snow twin and Pudge", "reveal pan", "gasp, music box swell, happy squeal"),
  jump(5, "snowy_hill", ["fizz"], note=" in a snowy puddle, snow puffs instead of splashes")]),
E(28, "The Hiccup Band 🥁", "The friends turn Drizzle's hiccups into a beat and form a meadow band, with tiny Bitsy as the conductor.",
  "Let's make a BAND!", "Hic, boom, ting! Drizzle and friends make music together.", ["music", "band", "rhythm"], "bouncy ukulele", [
  S(1, 8, "big_oak", ["drizzle", "pudge"], "Drizzle hiccuping in a steady rhythm, Pudge tapping his foot", "Pudge taps along to the hiccups", "medium shot", "'hic... hic... hic' in rhythm, foot taps"),
  S(2, 8, "big_oak", ["pudge", "fizz"], "Pudge drumming on an upturned bucket, Fizz shaking an acorn rattle", "they play along to the hiccup beat", "two-shot", "drum and rattle with hiccup beat"),
  S(3, 8, "big_oak", ["gran_tortle"], "Gran tapping a spoon on her shell like a xylophone", "Gran plays a tune on her shell", "close up", "shell xylophone tune"),
  S(4, 8, "big_oak", ["bitsy", "drizzle"], "Bitsy on a mushroom holding a twig baton", "Bitsy conducts and the band plays a happy song together", "wide band shot", "full happy cartoon band tune"),
  jump(5, "big_oak", ["fizz"], note=", final drum hit as they land")]),
E(29, "Drizzle's Shadow 🌤️", "Drizzle discovers her shadow on the meadow and plays tag with it, and Pudge and Fizz join the shadow game.",
  "Drizzle found her SHADOW!", "Shadow tag in the sunny meadow with Drizzle and Pudge.", ["shadow", "tag", "outdoor play"], "happy whistle", [
  S(1, 8, "meadow", ["drizzle"], "Drizzle looking down at a round cloud-shaped shadow on the grass", "Drizzle moves left, the shadow moves left; she gasps", "high angle", "curious 'ooh?'"),
  S(2, 8, "meadow", ["drizzle", "pudge"], "Pudge trying to jump onto Drizzle's shadow", "the shadow slides away each time, Pudge laughs", "wide shot", "boing hops, giggles"),
  S(3, 8, "meadow", ["fizz", "pudge"], "Fizz and Pudge making their own shadows into shapes", "their shadows make a funny two-headed monster shape and they laugh", "low angle with long shadows", "silly music sting, laughter"),
  S(4, 8, "meadow", ["drizzle", "pudge"], "all three shadows holding hands on the grass in a row", "they skip in a line, shadows skipping too", "high angle", "happy whistle melody"),
  jump(5, "meadow", ["fizz"])]),
E(30, "Glowing Winter Tree 🎄", "On the winter festival night Drizzle rains glowing star-lights onto Gran's tree and everyone celebrates with a snowy puddle jump.",
  "Light up the tree! ✨", "A cosy winter celebration with all the friends. Season finale of Drizzle & Pudge!", ["winter", "festive", "lights"], "magic twinkle", [
  S(1, 8, "snowy_hill", ["gran_tortle", "pudge"], "Gran and Pudge beside a small snowy fir tree at dusk", "they hang little paper decorations on the tree", "medium shot", "soft snow, warm hums"),
  S(2, 8, "snowy_hill", ["drizzle"], "Drizzle above the tree glowing, ready", "Drizzle rains glowing golden star-lights onto every branch", "slow tilt up the tree", "magic twinkle cascade"),
  S(3, 8, "snowy_hill", ["fizz", "bitsy"], "Fizz placing a big glowing star on top, Bitsy riding on the star", "the tree lights up fully, glowing warm and bright", "low angle hero shot", "gasp of wonder, chime"),
  S(4, 10, "snowy_hill", ["pudge", "gran_tortle"], "all the friends together in front of the glowing tree, a friendly smiling cloud in the sky", "everyone hugs and sways happily while gentle snow falls", "slow pull back", "warm festive melody, happy giggles"),
  jump(5, "snowy_hill", ["fizz"], note=" in a snowy puddle, snow puffs sparkling in the tree lights")]),
]

(OUT / "eps_001-015.json").write_text(json.dumps({"episodes": eps[:15]}, indent=1, ensure_ascii=False))
(OUT / "eps_016-030.json").write_text(json.dumps({"episodes": eps[15:]}, indent=1, ensure_ascii=False))
print(len(eps), "episodes written")
