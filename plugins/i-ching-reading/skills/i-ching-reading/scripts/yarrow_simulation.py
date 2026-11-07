#!/usr/bin/env python3
"""
Yarrow Stalk I Ching Simulation

Simulates the traditional yarrow stalk oracle method with correct
asymmetric probability distribution:

  6 (old yin, changing):   1/16  ━ ━ ×
  7 (young yang, stable):  5/16  ━━━━━
  8 (young yin, stable):   7/16  ━ ━
  9 (old yang, changing):  3/16  ━━━━━ ○

This differs from the three-coin method (equal 1/8 for 6 and 9)
in one structurally important way. Both methods cast yin and yang
lines equally often (1/2 each) and change a line with the same
probability (1/4). But under yarrow, when changes do occur, old
yang (9) is three times as likely as old yin (6), so the resulting
hexagram leans yin (5/8).

The asymmetry means the yarrow oracle has a different "personality"
than coins — not quieter or more often stable, but when it does
speak through changing lines, there's a directionality to the
change (yang changes more readily than yin).

Usage:
    python yarrow_simulation.py
    python yarrow_simulation.py --seed 42        # reproducible
    python yarrow_simulation.py --method coins    # three-coin probabilities
    python yarrow_simulation.py --json            # machine-readable output
"""

import random
import json
import sys
import datetime
import argparse


# ============================================================
# TRIGRAM DATA
# ============================================================

# Trigram tuple format: (line1_bottom, line2_middle, line3_top)
# where 1 = yang, 0 = yin

TRIGRAMS = {
    (1, 1, 1): {"name": "Qián",  "nature": "Heaven",    "symbol": "☰", "attribute": "strong",    "family": "father",          "animal": "horse",   "body": "head",  "direction": "NW", "element": "metal",  "season": "late autumn"},
    (0, 0, 0): {"name": "Kūn",   "nature": "Earth",     "symbol": "☷", "attribute": "devoted",   "family": "mother",          "animal": "ox",      "body": "belly", "direction": "SW", "element": "earth",  "season": "late summer"},
    (1, 0, 0): {"name": "Zhèn",  "nature": "Thunder",   "symbol": "☳", "attribute": "inciting",  "family": "eldest son",      "animal": "dragon",  "body": "foot",  "direction": "E",  "element": "wood",   "season": "spring"},
    (0, 1, 0): {"name": "Kǎn",   "nature": "Water",     "symbol": "☵", "attribute": "dangerous", "family": "middle son",      "animal": "pig",     "body": "ear",   "direction": "N",  "element": "water",  "season": "winter"},
    (0, 0, 1): {"name": "Gèn",   "nature": "Mountain",  "symbol": "☶", "attribute": "still",     "family": "youngest son",    "animal": "dog",     "body": "hand",  "direction": "NE", "element": "earth",  "season": "early spring"},
    (0, 1, 1): {"name": "Xùn",   "nature": "Wind/Wood", "symbol": "☴", "attribute": "gentle",    "family": "eldest daughter",  "animal": "cock",    "body": "thigh", "direction": "SE", "element": "wood",   "season": "early summer"},
    (1, 0, 1): {"name": "Lí",    "nature": "Fire",      "symbol": "☲", "attribute": "clinging",  "family": "middle daughter",  "animal": "pheasant","body": "eye",   "direction": "S",  "element": "fire",   "season": "summer"},
    (1, 1, 0): {"name": "Duì",   "nature": "Lake",      "symbol": "☱", "attribute": "joyous",    "family": "youngest daughter","animal": "sheep",   "body": "mouth", "direction": "W",  "element": "metal",  "season": "autumn"},
}

# Index mapping for King Wen table lookup
TRIGRAM_TO_INDEX = {
    (1, 1, 1): 0,  # Qián
    (1, 1, 0): 1,  # Duì
    (1, 0, 1): 2,  # Lí
    (1, 0, 0): 3,  # Zhèn
    (0, 1, 1): 4,  # Xùn
    (0, 1, 0): 5,  # Kǎn
    (0, 0, 1): 6,  # Gèn
    (0, 0, 0): 7,  # Kūn
}


# ============================================================
# KING WEN SEQUENCE
# ============================================================

# [lower_trigram_index][upper_trigram_index] -> hexagram number
#
# NOTE (2026-07-02 fix): this table was previously filled transposed --
# rows held the UPPER trigram and columns the LOWER, while
# get_hexagram_number() indexes it as [lower][upper]. Every asymmetric
# hexagram was therefore reported as its trigram-swapped partner
# (e.g. a cast of 54 Gui Mei reported as 17 Sui; resulting 7 Shi
# reported as 8 Bi; nuclear/complementary likewise). The table below
# is the corrected [lower][upper] orientation, verified against the
# line structure of the source texts (Hex 17 line 2 is yin, Hex 54
# line 2 is yang) and the doubled-trigram diagonal.
KING_WEN = [
    #  Qián Duì  Lí  Zhèn Xùn  Kǎn  Gèn  Kūn    <- upper trigram
    [   1,  43,  14,   34,   9,   5,  26,  11],   # Qián lower
    [  10,  58,  38,   54,  61,  60,  41,  19],   # Duì lower
    [  13,  49,  30,   55,  37,  63,  22,  36],   # Lí lower
    [  25,  17,  21,   51,  42,   3,  27,  24],   # Zhèn lower
    [  44,  28,  50,   32,  57,  48,  18,  46],   # Xùn lower
    [   6,  47,  64,   40,  59,  29,   4,   7],   # Kǎn lower
    [  33,  31,  56,   62,  53,  39,  52,  15],   # Gèn lower
    [  12,  45,  35,   16,  20,   8,  23,   2],   # Kūn lower
]


# ============================================================
# HEXAGRAM DATA — All 64
# ============================================================
# Format: number -> (pinyin, wilhelm_name, huang_name, judgment_essence, image_essence)
# huang_name is a legacy key: the set (Force, Field, ...) is not Alfred Huang's.
# judgment_essence and image_essence are original structural descriptions,
# not reproductions of any translation.

HEXAGRAMS = {
    1:  ("Qián",      "The Creative",              "Force",
         "Pure yang in all positions. Initiating power that doesn't yet meet resistance. The dragon's trajectory from hidden depths to overreaching height.",
         "Heaven moves ceaselessly. The superior person strengthens themselves without stopping."),
    2:  ("Kūn",       "The Receptive",              "Field",
         "Pure yin in all positions. Responsiveness as its own form of power — not passive but actively yielding. The mare who finds her way without leading.",
         "Earth's condition is receptive devotion. The superior person carries all things with broad virtue."),
    3:  ("Zhūn",      "Difficulty at the Beginning", "Sprouting",
         "Water over Thunder — clouds and thunder fill the sky but rain hasn't fallen yet. Initial difficulty of anything new breaking through. Chaos that precedes order. Don't try to force direction; appoint helpers.",
         "Clouds and thunder. The superior person sorts and arranges like threading silk."),
    4:  ("Méng",      "Youthful Folly",             "Enveloping",
         "Mountain over Water — a spring emerges at the base of a mountain but doesn't yet know its course. Not stupidity but inexperience. The student must come to the teacher, not the reverse.",
         "A spring wells up at the foot of the mountain. The superior person nurtures character through decisive action."),
    5:  ("Xū",        "Waiting",                    "Attending",
         "Water over Heaven — clouds risen high but rain not yet falling. Danger ahead but the timing isn't right to act. Nourish yourself while waiting. Trust the process.",
         "Clouds rise up to heaven. The superior person eats, drinks, and is at ease."),
    6:  ("Sòng",      "Conflict",                   "Arguing",
         "Heaven over Water — movement in opposite directions (heaven rises, water descends). Inner conviction meets outer danger. A strong case doesn't mean you should press it. Meet halfway; see the great person.",
         "Heaven and water go opposite ways. The superior person carefully begins all undertakings."),
    7:  ("Shī",       "The Army",                   "Leading",
         "Earth over Water — water contained within the earth, like an army within the people. Discipline through structure. Only a leader with genuine authority (the 'experienced one' in line 2) succeeds.",
         "Water in the midst of earth. The superior person nourishes the people and gathers them."),
    8:  ("Bǐ",        "Holding Together",           "Grouping",
         "Water over Earth — water flows on the earth and collects. Unity through natural affinity, not force. Late joiners lose out. Examine your own capacity to be the center before claiming that role.",
         "Water on earth flows together. Ancient kings established the myriad states and cultivated relations with feudal lords."),
    9:  ("Xiǎo Chù",  "Small Taming",              "Small Accumulating",
         "Wind over Heaven — gentle force restraining great force. Influence through gentle persistence, not confrontation. Dense clouds but no rain yet. Accumulate small gains.",
         "Wind moving across heaven. The superior person refines the outward expression of their nature."),
    10: ("Lǚ",        "Treading",                   "Treading",
         "Heaven over Lake — treading on the tail of the tiger. Conduct in dangerous situations. Cheerful (Lake) approach to power (Heaven) prevents being bitten. Propriety as practical survival.",
         "Heaven above, lake below. The superior person distinguishes upper and lower and gives the people fixed purpose."),
    11: ("Tài",       "Peace",                      "Pervading",
         "Earth over Heaven — the light rises, the heavy descends, so they meet and mingle. Heaven and earth in communion. Spring. Everything flows and connects. Inner strength, outer devotion.",
         "Heaven and earth unite. The ruler fashions and completes the course of heaven and earth."),
    12: ("Pǐ",        "Standstill",                 "Obstruction",
         "Heaven over Earth — each moves away from the other, no interchange. Stagnation. The inferior rises, the superior retreats. Not a time for action but for inner perseverance and withdrawing from corruption.",
         "Heaven and earth do not unite. The superior person withdraws into their inner worth."),
    13: ("Tóng Rén",  "Fellowship",                 "Concording People",
         "Heaven over Fire — fire's nature is to flame upward toward heaven. Fellowship based on shared clarity, not cliquishness. Success comes through openness (in the open, not behind closed doors).",
         "Heaven together with fire. The superior person organizes clans and distinguishes things."),
    14: ("Dà Yǒu",   "Great Possession",           "Great Possessing",
         "Fire over Heaven — fire high in the sky illuminates everything. Abundance through clarity and strength combined. The yielding line in the fifth position rules all the strong lines — power held through modesty.",
         "Fire in heaven above. The superior person curbs evil and promotes good, following heaven's mandate."),
    15: ("Qiān",      "Modesty",                    "Humbling",
         "Earth over Mountain — a mountain's wealth hidden beneath the earth. The one hexagram where every line is favorable. Modesty not as weakness but as the great equalizer — it fills what is empty, diminishes what is full.",
         "A mountain within the earth. The superior person reduces what is too much, augments what is too little, weighing things to make them equal."),
    16: ("Yù",        "Enthusiasm",                 "Providing-for",
         "Thunder over Earth — thunder bursting from the earth in spring. Movement that arises from natural devotion, not forced excitement. Time for setting things in motion. Install helpers, move armies.",
         "Thunder comes forth from the earth with vigor. The ancient kings made music to honor virtue."),
    17: ("Suí",       "Following",                  "Following",
         "Lake over Thunder — thunder at rest beneath the lake, joy above movement. Following and being followed as reciprocal. Adapt to the time. Rest when it's time to rest.",
         "Thunder in the middle of the lake. The superior person at nightfall goes inside to rest."),
    18: ("Gǔ",        "Work on the Decayed",        "Correcting",
         "Mountain over Wind — wind stopped at the base of a mountain, stagnation. Decay that must be corrected — a bowl with worms in it. Three days before and after the turning point. Inherited problems requiring active remedy.",
         "Wind blows low on the mountain. The superior person stirs up the people and nourishes their virtue."),
    19: ("Lín",       "Approach",                   "Nearing",
         "Earth over Lake — the lake filling toward the earth above. Approach of something powerful. Time of growth and increase, but awareness that by the eighth month, decline begins. Use the time of increase wisely.",
         "Earth above the lake. The superior person is inexhaustible in their will to teach and unlimited in their tolerance and protection of the people."),
    20: ("Guān",      "Contemplation",              "Viewing",
         "Wind over Earth — wind blowing over the earth, reaching everywhere. Seeing and being seen. The tower from which one contemplates the land. Wash hands but don't yet make the offering — the moment of serious attention before action.",
         "Wind moves over the earth. Ancient kings visited the regions to observe the people and set forth instruction."),
    21: ("Shì Kè",    "Biting Through",             "Gnawing Bite",
         "Fire over Thunder — lightning and thunder together. Something obstructing the jaws must be bitten through. Legal action, decisive force to remove obstacles. The nature of the obstruction determines the force required.",
         "Thunder and lightning. Ancient kings made penalties clear through firm laws."),
    22: ("Bì",        "Grace",                      "Adorning",
         "Mountain over Fire — fire at the foot of the mountain, illuminating it softly. Beauty and form. Grace succeeds in small matters. Don't mistake the ornament for the substance — form serves content.",
         "Fire at the foot of the mountain. The superior person clarifies current affairs but doesn't dare decide great controversies this way."),
    23: ("Bō",        "Splitting Apart",            "Stripping",
         "Mountain over Earth — the mountain's base eroding until only a thin peak remains. Five yin lines stripping away the last yang. Not a time to go anywhere. The inferior displaces the superior. Wait; the cycle will turn.",
         "The mountain rests on the earth. Those above can only ensure their position by giving generously to those below."),
    24: ("Fù",        "Return",                     "Returning",
         "Earth over Thunder — thunder within the earth, the first stirring of return. The winter solstice, the turning point. One yang line returns at the bottom. After splitting apart, return. Seven days. Don't chase it; let it come naturally.",
         "Thunder within the earth. Ancient kings closed the passes at the solstice, merchants did not travel, and the ruler did not inspect the regions."),
    25: ("Wú Wàng",   "Innocence",                  "Without Embroiling",
         "Heaven over Thunder — natural movement under heaven. Action without ulterior calculation. What is not expected cannot be sought. If not right, there will be misfortune — don't act from false innocence.",
         "Under heaven, thunder rolls. All things attain their natural state. Ancient kings nourished all beings in accord with the season."),
    26: ("Dà Chù",    "Great Taming",               "Great Accumulating",
         "Mountain over Heaven — heaven's force held within the mountain. Great accumulation of energy, knowledge, or resources. Don't eat at home — go out and serve. Study the past to understand the present.",
         "Heaven within the mountain. The superior person studies the words and deeds of the past to accumulate virtue."),
    27: ("Yí",        "Nourishment",                "Swallowing",
         "Mountain over Thunder — the mouth (stillness above, movement below). What you take in and what you put out. Watch what a person nourishes in themselves and others to know their character.",
         "Thunder under the mountain. The superior person is careful with words and temperate in eating and drinking."),
    28: ("Dà Guò",    "Great Exceeding",            "Great Exceeding",
         "Lake over Wind — the ridgepole sags, excess weight. The great exceeding the normal. Four yang lines overpowering two yin at the extremes. Extraordinary measures needed. The tree standing alone, the unmarried elder — images of going beyond convention.",
         "The lake submerges the trees. The superior person stands alone without fear and withdraws from the world without melancholy."),
    29: ("Kǎn",       "The Abysmal",                "Gorge",
         "Water over Water — doubled danger, pit within pit. Water flows and doesn't accumulate, just fills each pit and moves on. The heart can penetrate danger because it maintains its own constancy. Practice teaches, like water repeated.",
         "Water flows and reaches the goal. The superior person walks in lasting virtue and practices the business of teaching."),
    30: ("Lí",        "The Clinging",               "Radiance",
         "Fire over Fire — doubled fire/radiance. Fire needs something to cling to in order to give light. Brightness as dependent on what it illuminates. Care for what you tend, and the light sustains. The cow as image of docile yielding that enables brilliance.",
         "That which is bright rises twice. The great person perpetuates the illumination by shining on the four regions."),
    31: ("Xián",      "Influence",                  "Conjoining",
         "Lake over Mountain — the youngest daughter above the youngest son. Mutual attraction, sensitivity, influence without force. Keep still below (mountain) and be open above (lake). The image of courtship — genuine influence flows from receptivity.",
         "A lake on the mountain. The superior person receives people with open emptiness."),
    32: ("Héng",      "Duration",                   "Persevering",
         "Thunder over Wind — the eldest son above the eldest daughter. Not rigidity but the consistency that adapts while maintaining direction. Thunder and wind reinforce each other endlessly. Endurance through movement within structure.",
         "Thunder and wind. The superior person stands firm and does not change direction."),
    33: ("Dùn",       "Retreat",                    "Retiring",
         "Heaven over Mountain — heaven receding upward from the mountain. Strategic withdrawal, not defeat. The small (yin) are advancing; the great withdraw at the right moment. Retreat with strength, not bitterness.",
         "Mountain under heaven. The superior person keeps the inferior at a distance, not with anger but with reserve."),
    34: ("Dà Zhuàng", "Great Power",                "Great Invigorating",
         "Thunder over Heaven — power in motion, four yang lines pressing upward. Great strength. Danger of using power without righteousness. The ram butting a hedge — strength without wisdom gets entangled.",
         "Thunder above heaven. The superior person does not tread paths that are not in accord with proper order."),
    35: ("Jìn",       "Progress",                   "Prospering",
         "Fire over Earth — the sun rising over the earth. Rapid, easy progress. The prince receives horses in abundance and audience three times in a day. Advance through clarity, not through force.",
         "The sun rises over the earth. The superior person brightens their bright virtue."),
    36: ("Míng Yí",   "Darkening of the Light",     "Brightness Hiding",
         "Earth over Fire — the sun has sunk beneath the earth. Brilliance wounded, intelligence concealed. Protect your inner light when the outer situation is dark. King Wen imprisoned, Prince Ji feigning madness — survival through hiddenness.",
         "The light has sunk into the earth. The superior person lives with the multitude, veiling their brightness yet still shining."),
    37: ("Jiā Rén",   "The Family",                 "Dwelling People",
         "Wind over Fire — wind born from fire, warmth radiating outward. The inner warmth (fire/clarity) generates the outer influence (wind/gentle penetration). Begin with yourself, then your household, then the world. Words must have substance, conduct must have consistency.",
         "Wind comes forth from fire. The superior person's words have substance and their conduct has consistency."),
    38: ("Kuí",       "Opposition",                 "Polarizing",
         "Fire over Lake — fire flames upward, lake water flows downward, moving apart. Opposition in small matters, not in great ones. Estranged people finding unexpected connections. The fire and lake don't merge but each maintains its nature while relating.",
         "Fire above, lake below. The superior person remains an individual even in community."),
    39: ("Jiǎn",      "Obstruction",                "Limping",
         "Water over Mountain — dangerous water on the mountain path. The southwest (level ground) brings progress; the northeast (mountain) doesn't. See the great person. Turn inward, don't push forward against the obstruction.",
         "Water on the mountain. The superior person turns around and examines themselves, cultivating virtue."),
    40: ("Jiě",       "Deliverance",                "Taking-apart",
         "Thunder over Water — thunder and rain dissolving tension. After obstruction, release. Return to normal as quickly as possible; don't linger in the drama of liberation. Forgive transgressions, be lenient with faults.",
         "Thunder and rain arise. The superior person forgives transgressions and pardons faults."),
    41: ("Sǔn",       "Decrease",                   "Diminishing",
         "Mountain over Lake — the mountain rises, the lake decreases below. Decrease below to increase above. Genuine sacrifice, not resentment. Even with simple offerings, sincerity makes them sufficient. Decrease of excess leads to balance.",
         "A lake at the foot of the mountain. The superior person controls anger and restrains instincts."),
    42: ("Yì",        "Increase",                   "Augmenting",
         "Wind over Thunder — wind and thunder increase each other. Decrease above to increase below. When you see good, move toward it; when you see faults in yourself, correct them. Time for undertaking — cross the great water.",
         "Wind and thunder. The superior person, seeing good, imitates it; having faults, corrects them."),
    43: ("Guài",      "Breakthrough",               "Displacement",
         "Lake over Heaven — the last yin line at the top, five yang lines pressing upward. One remaining inferior element must be dealt with openly, not by force but by bringing it to light. Announce it in the king's court. Danger in the process — taking up arms does not serve.",
         "The lake has risen up to heaven. The superior person distributes riches downward and avoids resting in virtue."),
    44: ("Gòu",       "Coming to Meet",             "Coupling",
         "Heaven over Wind — a yin line enters from below. An unexpected encounter, the inferior approaching. The bold girl — don't marry her. Recognize the small that returns and don't let it gain power unconsciously. Not about rejection but about awareness.",
         "Under heaven there is wind. The prince issues commands and proclaims them to the four quarters."),
    45: ("Cuì",       "Gathering Together",          "Clustering",
         "Lake over Earth — the lake formed above the earth, water gathering. Collection of people and resources. Bring great offerings. See the great person. Guard against the unexpected even in gathering — have weapons ready not for attack but for defense.",
         "The lake is above the earth. The superior person puts weapons in order to guard against the unforeseen."),
    46: ("Shēng",     "Pushing Upward",             "Ascending",
         "Earth over Wind — wood grows within the earth, pushing upward. Gradual rise through effort, growth that follows natural pattern. See the great person, don't worry. Pushing upward to the south brings good fortune.",
         "Within the earth, wood grows. The superior person with devoted attention accumulates small things to achieve what is high and great."),
    47: ("Kùn",       "Oppression",                 "Confining",
         "Lake over Water — the lake drained, water below unavailable. Exhaustion. Words are not believed. The great person finds good fortune through perseverance — but only because they exhaust their fate before speaking. Cheerfulness in difficult circumstances.",
         "There is no water in the lake. The superior person stakes their life on following their will."),
    48: ("Jǐng",      "The Well",                   "Welling",
         "Water over Wind/Wood — wood dipping into water and drawing it up. The well: the town may move, but the well stays. Inexhaustible resource if properly maintained. Nearly reaching the water but not quite getting the bucket down — misfortune of incompletion.",
         "Water over wood. The superior person encourages the people at their work and exhorts them to help one another."),
    49: ("Gé",        "Revolution",                 "Skinning",
         "Lake over Fire — fire and water in the lake, each trying to destroy the other. Radical change. Only believed after completion — only on your own day (this reads 己日; the bundled text has 巳日, a textual variant: UNRESOLVED). Timing is everything: first remorse, then a complete skinning of the old. The animal's skin changed with the seasons.",
         "Fire in the lake. The superior person sets the calendar in order and makes the seasons clear."),
    50: ("Dǐng",      "The Caldron",                "Holding",
         "Fire over Wind/Wood — wood feeding fire, the image of the ritual cooking vessel. Transformation through the proper vessel. The ding transforms raw into cooked, crude into refined. Supreme good fortune when the vessel has yellow handles and golden, then jade, rings — function and form aligned.",
         "Fire over wood. The superior person consolidates fate by making their position correct."),
    51: ("Zhèn",      "The Arousing",               "Shake",
         "Thunder over Thunder — doubled thunder. Shock that comes and goes, the terrifying made productive. The shock comes — oh, oh! Laughing words — ha, ha! Shock for a hundred miles but doesn't drop the sacrificial spoon and chalice. Composure within disruption.",
         "Thunder repeated. The superior person in fear and trembling examines themselves and sets things in order."),
    52: ("Gèn",       "Keeping Still",              "Bound",
         "Mountain over Mountain — doubled mountain. Stillness so complete you don't perceive your own body, walk in the courtyard and don't see the people. Not suppression but achieved stillness — the back (which the person cannot see) as the image of resting in the right place without restlessness.",
         "Mountains standing close together. The superior person does not let their thoughts go beyond their position."),
    53: ("Jiàn",      "Development",                "Infiltrating",
         "Wind/Wood over Mountain — a tree on the mountain grows slowly but steadily. Gradual development. The wild goose approaching the shore in stages. The marrying maiden progresses through proper stages. What develops gradually endures.",
         "On the mountain a tree grows. The superior person abides in dignity and virtue to improve the mores."),
    54: ("Guī Mèi",   "The Marrying Maiden",        "Converting the Maiden",
         "Thunder over Lake — the eldest son above the youngest daughter. Moving (thunder) through joy (lake) without propriety. The subordinate position entered willingly. Undertakings bring misfortune — but the situation isn't inherently bad, just requiring careful navigation of asymmetric power.",
         "Thunder over the lake. The superior person understands the transitory in light of the eternal."),
    55: ("Fēng",      "Abundance",                  "Abounding",
         "Thunder over Fire — lightning and thunder together in full force. Maximum brightness and maximum movement. Zenith — don't be sad, be like the sun at midday. Abundance cannot last; the awareness of this IS the wisdom, not a call to prevent it.",
         "Thunder and lightning both arrive. The superior person decides lawsuits and carries out punishments."),
    56: ("Lǚ",        "The Wanderer",               "Sojourning",
         "Fire over Mountain — fire on the mountain, bright but moving on, not staying. The traveler, the stranger, the exile. Success through being small and careful. Fire doesn't cling to the mountain — it passes through. Propriety and alertness in unfamiliar territory.",
         "Fire on the mountain. The superior person is clear-minded and cautious in imposing penalties, and doesn't drag out lawsuits."),
    57: ("Xùn",       "The Gentle",                 "Ground",
         "Wind over Wind — doubled wind/penetration. Gentle but persistent influence. Success through small, repeated effects rather than dramatic force. See the great person. Take small actions. Like wind, the message penetrates everywhere gradually.",
         "Winds following one upon another. The superior person reiterates commands to carry out affairs."),
    58: ("Duì",       "The Joyous",                 "Open",
         "Lake over Lake — doubled joy/openness. Joy that communicates, not solitary pleasure. Success through joyousness. Firm inside, yielding outside. Friends join in discussion and practice — mutual encouragement in study. Genuine joy as a force that dissolves difficulties.",
         "Lakes resting one on the other. The superior person joins with friends for discussion and practice."),
    59: ("Huàn",      "Dispersion",                 "Dispersing",
         "Wind over Water — wind blowing across water, breaking up rigid accumulations. Dissolving egotism, rigidity, and separation. The king approaches the temple — use shared meaning to reunite what has scattered. Cross the great water.",
         "Wind drives over water. Ancient kings made offerings to the Lord and established temples."),
    60: ("Jié",       "Limitation",                 "Articulating",
         "Water over Lake — the lake has bounds, water is contained. Joints, nodes, seasons — the articulation points that give structure. Galling limitation should not be persevered in. Limits make meaning possible (like joints make movement possible), but excessive limitation breaks.",
         "Water above the lake. The superior person creates number and measure, and examines the nature of virtue and correct conduct."),
    61: ("Zhōng Fú",  "Inner Truth",                "Center Returning",
         "Wind over Lake — wind blowing over the lake stirs the surface. Inner truth, central sincerity. Pigs and fishes — even the lowest and dimmest are moved by genuine sincerity. The empty center (two yin lines in the middle) IS the capacity for truth — like a hollow vessel that can receive.",
         "Wind over the lake. The superior person discusses criminal cases to delay executions."),
    62: ("Xiǎo Guò",  "Small Exceeding",            "Small Exceeding",
         "Thunder over Mountain — thunder on the mountain, closer and louder but passing quickly. The flying bird — go downward, not upward. In small things exceeding is possible and proper; in great things, not. The form of the hexagram (four yin outside, two yang inside) shows small things surrounding and exceeding the great.",
         "Thunder on the mountain. The superior person in conduct exceeds in humility, in mourning exceeds in sorrow, in expenditures exceeds in thrift."),
    63: ("Jì Jì",     "After Completion",           "Already Fording",
         "Water over Fire — fire below, water above, each in its proper place. Everything in order, everything in position. Complete — which means the only direction is toward disorder. A wet tail at the start (line 1), a wet head at the end (line 6). Success in small matters. Initial good fortune, final disorder.",
         "Water over fire. The superior person reflects on misfortune and arms against it in advance."),
    64: ("Wèi Jì",    "Before Completion",          "Not Yet Fording",
         "Fire over Water — fire above, water below, each moving away. Nothing in its proper place yet. The young fox nearly across but gets its tail wet. Everything is still becoming. The final hexagram is incompletion — the cycle never truly closes, which IS the vitality.",
         "Fire above water. The superior person carefully discriminates among things and keeps each in its place."),
}


# ============================================================
# STRUCTURAL DATA: Ruling lines, nuclear hexagrams
# ============================================================

# Ruling line(s) for each hexagram (1-indexed from bottom)
# These are the constituting rulers — the line(s) that define the hexagram's character
RULING_LINES = {
    1: [5], 2: [5], 3: [1], 4: [5], 5: [5], 6: [5], 7: [2], 8: [5],
    9: [4], 10: [3], 11: [5], 12: [5], 13: [2, 5], 14: [5], 15: [3], 16: [4],
    17: [1], 18: [5], 19: [1, 2], 20: [5], 21: [5], 22: [6], 23: [6], 24: [1],
    25: [1], 26: [6], 27: [1, 6], 28: [2, 5], 29: [5], 30: [2, 5], 31: [4, 5], 32: [2],
    33: [5], 34: [4], 35: [5], 36: [5], 37: [2], 38: [5], 39: [5], 40: [2],
    41: [3], 42: [5], 43: [5], 44: [1], 45: [4, 5], 46: [2], 47: [2, 5], 48: [5],
    49: [5], 50: [5], 51: [4], 52: [3], 53: [5], 54: [5], 55: [2], 56: [5],
    57: [5], 58: [5], 59: [5], 60: [5], 61: [2], 62: [2], 63: [5], 64: [5],
}


# ============================================================
# LINE GENERATION
# ============================================================

def yarrow_line():
    """Generate one line using yarrow stalk probability distribution."""
    r = random.randint(0, 15)
    if r == 0:          return 6   # old yin (changing):  1/16
    elif r <= 5:        return 7   # young yang (stable): 5/16
    elif r <= 12:       return 8   # young yin (stable):  7/16
    else:               return 9   # old yang (changing): 3/16


def coin_line():
    """Generate one line using three-coin probability distribution."""
    r = random.randint(0, 7)
    if r == 0:          return 6   # old yin:   1/8
    elif r <= 3:        return 7   # young yang: 3/8
    elif r <= 6:        return 8   # young yin:  3/8
    else:               return 9   # old yang:  1/8


# ============================================================
# HEXAGRAM ANALYSIS
# ============================================================

def lines_to_trigram(l1, l2, l3):
    """Convert three line values to trigram tuple. Yang (7,9)=1, Yin (6,8)=0."""
    return (
        1 if l1 in (7, 9) else 0,
        1 if l2 in (7, 9) else 0,
        1 if l3 in (7, 9) else 0,
    )


def changed_line(val):
    """Return the value a changing line transforms into."""
    if val == 6:  return 7   # old yin -> young yang
    if val == 9:  return 8   # old yang -> young yin
    return val


def get_hexagram_number(lower_tri, upper_tri):
    """Look up King Wen hexagram number from lower and upper trigram tuples."""
    li = TRIGRAM_TO_INDEX[lower_tri]
    ui = TRIGRAM_TO_INDEX[upper_tri]
    return KING_WEN[li][ui]


def nuclear_hexagram(lines):
    """
    Calculate the nuclear (inner) hexagram.
    Lower nuclear trigram = lines 2, 3, 4
    Upper nuclear trigram = lines 3, 4, 5
    """
    # Convert to binary first
    binary = [1 if v in (7, 9) else 0 for v in lines]
    nuc_lower = (binary[1], binary[2], binary[3])
    nuc_upper = (binary[2], binary[3], binary[4])
    return get_hexagram_number(nuc_lower, nuc_upper), nuc_lower, nuc_upper


def complementary_hexagram(lines):
    """Invert every line (yang<->yin) to get the complementary hexagram."""
    inverted = []
    for v in lines:
        if v in (7, 9):
            inverted.append(8)
        else:
            inverted.append(7)
    lower = lines_to_trigram(inverted[0], inverted[1], inverted[2])
    upper = lines_to_trigram(inverted[3], inverted[4], inverted[5])
    return get_hexagram_number(lower, upper)


def line_display(val, position):
    """Return display string for a line."""
    symbols = {
        6: "━ ━  ×",     # old yin, changing
        7: "━━━━━",       # young yang
        8: "━ ━",         # young yin
        9: "━━━━━ ○",     # old yang, changing
    }
    types = {
        6: "old yin (changing → yang)",
        7: "young yang",
        8: "young yin",
        9: "old yang (changing → yin)",
    }
    return symbols[val], types[val]


# ============================================================
# BITWISE (v, c) LAYER
# ============================================================
# Each line carries two binary coordinates:
#   v = value bit   : 1 = yang, 0 = yin
#   c = changing bit : 1 = changing, 0 = stable
# The resulting hexagram's value per line is v XOR c.
#   7 -> (1, 0)   8 -> (0, 0)   9 -> (1, 1)   6 -> (0, 1)
VC_MAP = {7: (1, 0), 8: (0, 0), 9: (1, 1), 6: (0, 1)}
VC_INVERSE = {vc: val for val, vc in VC_MAP.items()}


def value_to_vc(val):
    """Map a cast value (6/7/8/9) to its (v, c) bit pair."""
    return VC_MAP[val]


def vc_to_value(v, c):
    """Map a (v, c) bit pair back to its cast value (6/7/8/9)."""
    return VC_INVERSE[(v, c)]


def resulting_line_value(val):
    """Resulting hexagram's (stable) line value: 7 if v XOR c else 8.

    Equivalent to changed_line(val) by construction; kept as a separate
    XOR-derived path so the bitwise layer is self-verifying against the
    traditional changing-line computation.
    """
    v, c = value_to_vc(val)
    return 7 if (v ^ c) else 8


def _binary_layer_lines(reading):
    """Render the optional bitwise (v, c) layer for the text reading."""
    lines = reading["lines"]
    out = ["── Bitwise (v, c) Layer ──",
           "  v = value bit (1 yang / 0 yin),  c = changing bit (1 / 0).",
           "  The resulting hexagram is the per-line XOR:  result = v XOR c.",
           ""]
    for i in range(5, -1, -1):
        val = lines[i]
        v, c = value_to_vc(val)
        rv = v ^ c
        glyph = "━━━━━" if rv else "━ ━"
        out.append(
            "  Line %d:  %d  (v=%d, c=%d)   %d XOR %d = %d  →  %s (%s)"
            % (i + 1, val, v, c, v, c, rv, glyph, "yang" if rv else "yin")
        )
    out.append("")
    primary = reading["primary_hexagram"]["number"]
    if reading["changing_lines"]:
        resulting = reading["resulting_hexagram"]["number"]
        out.append("  Primary → Hexagram %d" % primary)
        out.append("  After XOR (changing bits applied) → Resulting Hexagram %d" % resulting)
        out.append("  (matches the Resulting Hexagram above)")
    else:
        out.append("  Primary → Hexagram %d" % primary)
        out.append("  All changing bits = 0 → XOR is identity → Resulting hexagram = Primary.")
    return out


# ============================================================
# READING GENERATION
# ============================================================

def generate_reading(method="yarrow", seed=None):
    """
    Generate a complete I Ching reading.

    Returns a dict with all structural information needed for interpretation.
    """
    if seed is not None:
        random.seed(seed)

    line_fn = yarrow_line if method == "yarrow" else coin_line

    lines = [line_fn() for _ in range(6)]

    lower_tri = lines_to_trigram(lines[0], lines[1], lines[2])
    upper_tri = lines_to_trigram(lines[3], lines[4], lines[5])

    hex_num = get_hexagram_number(lower_tri, upper_tri)
    hex_data = HEXAGRAMS[hex_num]

    # Nuclear hexagram
    nuc_num, nuc_lower, nuc_upper = nuclear_hexagram(lines)
    nuc_data = HEXAGRAMS[nuc_num]

    # Complementary hexagram
    comp_num = complementary_hexagram(lines)
    comp_data = HEXAGRAMS[comp_num]

    # Changing lines
    changing = [i for i, v in enumerate(lines) if v in (6, 9)]

    result = {
        "timestamp": datetime.datetime.now().isoformat(),
        "method": method,
        "lines": lines,
        "lower_trigram": {
            "tuple": lower_tri,
            **TRIGRAMS[lower_tri],
        },
        "upper_trigram": {
            "tuple": upper_tri,
            **TRIGRAMS[upper_tri],
        },
        "primary_hexagram": {
            "number": hex_num,
            "pinyin": hex_data[0],
            "wilhelm_name": hex_data[1],
            "huang_name": hex_data[2],
            "judgment_essence": hex_data[3],
            "image_essence": hex_data[4],
            "ruling_lines": RULING_LINES.get(hex_num, []),
        },
        "nuclear_hexagram": {
            "number": nuc_num,
            "pinyin": nuc_data[0],
            "wilhelm_name": nuc_data[1],
            "huang_name": nuc_data[2],
            "judgment_essence": nuc_data[3],
            "lower_trigram": TRIGRAMS[nuc_lower],
            "upper_trigram": TRIGRAMS[nuc_upper],
        },
        "complementary_hexagram": {
            "number": comp_num,
            "pinyin": comp_data[0],
            "wilhelm_name": comp_data[1],
            "huang_name": comp_data[2],
        },
        "changing_lines": changing,
        "changing_line_positions": [c + 1 for c in changing],  # 1-indexed
    }

    # Resulting hexagram (if there are changing lines)
    if changing:
        changed_lines = [changed_line(v) for v in lines]
        res_lower = lines_to_trigram(changed_lines[0], changed_lines[1], changed_lines[2])
        res_upper = lines_to_trigram(changed_lines[3], changed_lines[4], changed_lines[5])
        res_num = get_hexagram_number(res_lower, res_upper)
        res_data = HEXAGRAMS[res_num]
        result["resulting_hexagram"] = {
            "number": res_num,
            "pinyin": res_data[0],
            "wilhelm_name": res_data[1],
            "huang_name": res_data[2],
            "judgment_essence": res_data[3],
            "image_essence": res_data[4],
            "ruling_lines": RULING_LINES.get(res_num, []),
            "lower_trigram": {
                "tuple": res_lower,
                **TRIGRAMS[res_lower],
            },
            "upper_trigram": {
                "tuple": res_upper,
                **TRIGRAMS[res_upper],
            },
        }

    # Structural analysis flags
    result["structural_notes"] = []

    if lower_tri == upper_tri:
        result["structural_notes"].append(
            f"DOUBLED TRIGRAM: {TRIGRAMS[lower_tri]['nature']} above and below. "
            f"The pattern repeats at both scales — inner mirrors outer."
        )

    if len(changing) == 0:
        result["structural_notes"].append(
            "NO CHANGING LINES: The situation is stable as described. "
            "No transformation is in process. This is what it IS."
        )
    elif len(changing) == 6:
        # Hexagrams 1 and 2 carry their own all-changing statement in the text
        # (references/zhouyi-source.json, extra_line_zh); changing-lines.md says it applies.
        all_changing_text = {1: "用九", 2: "用六"}.get(hex_num)
        if all_changing_text:
            result["structural_notes"].append(
                "ALL LINES CHANGING: Total transformation. "
                f"Hexagram {hex_num} has its own statement for this case, {all_changing_text} "
                "(extra_line_zh in references/zhouyi-source.json); read it."
            )
        else:
            result["structural_notes"].append(
                "ALL LINES CHANGING: Total transformation. "
                "The primary hexagram is entirely in flux; read the resulting hexagram as primary."
            )
    elif len(changing) == 1:
        result["structural_notes"].append(
            f"SINGLE CHANGING LINE (line {changing[0]+1}): "
            f"The transformation is focused and specific. "
            f"This line carries the entire dynamic of the reading."
        )

    yang_count = sum(1 for v in lines if v in (7, 9))
    yin_count = 6 - yang_count
    if yang_count == 1:
        pos = next(i for i, v in enumerate(lines) if v in (7, 9))
        result["structural_notes"].append(
            f"SINGLE YANG LINE (position {pos+1}): "
            f"One active element among five receptive. This yang line governs the hexagram."
        )
    elif yin_count == 1:
        pos = next(i for i, v in enumerate(lines) if v in (6, 8))
        result["structural_notes"].append(
            f"SINGLE YIN LINE (position {pos+1}): "
            f"One receptive element among five active. This yin line governs the hexagram."
        )

    # Check if any changing lines are ruling lines
    if changing:
        ruling = RULING_LINES.get(hex_num, [])
        ruling_changing = [c + 1 for c in changing if (c + 1) in ruling]
        if ruling_changing:
            result["structural_notes"].append(
                f"RULING LINE(S) CHANGING: Line(s) {ruling_changing} "
                f"are both ruling and changing — the hexagram's defining quality is in transformation."
            )

    return result


def format_reading(reading, binary=False):
    """Format a reading as human-readable text.

    binary=True appends the bitwise (v, c) layer; default output is unchanged.
    """
    output = []
    output.append("=" * 58)
    output.append("     YARROW STALK I CHING READING")
    output.append(f"     Method: {reading['method']}")
    output.append(f"     {datetime.datetime.now().strftime('%A, %B %d, %Y %H:%M')}")
    output.append("=" * 58)
    output.append("")

    output.append("The six lines (bottom → top):")
    output.append("")

    for i in range(5, -1, -1):
        val = reading["lines"][i]
        sym, desc = line_display(val, i + 1)
        marker = ""
        if (i + 1) in reading["primary_hexagram"]["ruling_lines"]:
            marker = " ★"
        output.append(f"  Line {i+1}:  {sym}   ({val} — {desc}){marker}")

    output.append("")
    output.append("  ★ = ruling line")
    output.append("")

    lt = reading["lower_trigram"]
    ut = reading["upper_trigram"]
    output.append(f"Lower trigram: {lt['symbol']} {lt['name']} ({lt['nature']})")
    output.append(f"  Attribute: {lt['attribute']} | Family: {lt['family']} | Direction: {lt['direction']}")
    output.append(f"Upper trigram: {ut['symbol']} {ut['name']} ({ut['nature']})")
    output.append(f"  Attribute: {ut['attribute']} | Family: {ut['family']} | Direction: {ut['direction']}")
    output.append("")

    ph = reading["primary_hexagram"]
    output.append(f"═══ PRIMARY HEXAGRAM: {ph['number']}. {ph['pinyin']} ═══")
    output.append(f"  Wilhelm: \"{ph['wilhelm_name']}\"")
    output.append(f"  Alt.:    \"{ph['huang_name']}\"")
    output.append(f"  Ruling line(s): {ph['ruling_lines']}")
    output.append("")
    output.append(f"  JUDGMENT: {ph['judgment_essence']}")
    output.append("")
    output.append(f"  IMAGE: {ph['image_essence']}")

    if reading["changing_lines"]:
        output.append("")
        output.append(f"  CHANGING LINES: {reading['changing_line_positions']}")

        rh = reading["resulting_hexagram"]
        output.append("")
        output.append(f"═══ RESULTING HEXAGRAM: {rh['number']}. {rh['pinyin']} ═══")
        output.append(f"  Wilhelm: \"{rh['wilhelm_name']}\"")
        output.append(f"  Alt.:    \"{rh['huang_name']}\"")
        output.append("")
        output.append(f"  JUDGMENT: {rh['judgment_essence']}")
        output.append("")
        output.append(f"  IMAGE: {rh['image_essence']}")

    nh = reading["nuclear_hexagram"]
    output.append("")
    output.append(f"  NUCLEAR: {nh['number']}. {nh['pinyin']} — \"{nh['wilhelm_name']}\"")
    output.append(f"    (The hidden inner dynamic)")

    ch = reading["complementary_hexagram"]
    output.append("")
    output.append(f"  COMPLEMENTARY: {ch['number']}. {ch['pinyin']} — \"{ch['wilhelm_name']}\"")
    output.append(f"    (The shadow / what is absent)")

    if reading["structural_notes"]:
        output.append("")
        output.append("── Structural Notes ──")
        for note in reading["structural_notes"]:
            output.append(f"  • {note}")

    if binary:
        output.append("")
        output.extend(_binary_layer_lines(reading))

    output.append("")
    output.append("=" * 58)

    return "\n".join(output)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yarrow Stalk I Ching Oracle")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--method", choices=["yarrow", "coins"], default="yarrow",
                       help="Divination method (default: yarrow)")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON instead of formatted text")
    parser.add_argument("--binary", action="store_true",
                       help="Append the bitwise (v, c) layer showing each line's "
                            "value/changing bits and the XOR to the resulting hexagram")
    args = parser.parse_args()

    reading = generate_reading(method=args.method, seed=args.seed)

    if args.json:
        # Convert tuples to lists for JSON serialization
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(i) for i in obj]
            return obj
        print(json.dumps(make_serializable(reading), indent=2))
    else:
        print(format_reading(reading, binary=args.binary))
