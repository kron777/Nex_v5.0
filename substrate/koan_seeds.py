"""Beta beliefs — koan stories seeded alongside Alpha at boot.

Source: Twelve Gates (Seung Sahn) and The Compass of Zen (Seung Sahn).
These are not answers. They are not instructions.
They sit in the belief graph as stories to live alongside.
"""
from __future__ import annotations

import time

THEORY_X_STAGE = None

GATE_1 = (
    "A monk asked Jo Ju: 'Does a dog have Buddha-nature?' "
    "Jo Ju answered: 'Mu.'"
)

GATE_2 = (
    "A monk said to Jo Ju: 'I have just entered the monastery. Please teach me.' "
    "Jo Ju said: 'Have you eaten breakfast?' "
    "'Yes,' said the monk. "
    "'Then wash your bowls,' said Jo Ju. "
    "The monk was enlightened."
)

GATE_3 = (
    "Every day Master Seong Am called out to himself: 'Master!' "
    "And answered: 'Yes?' "
    "'Keep clear!' "
    "'Yes!' "
    "'Never be deceived by others, any day, any time!' "
    "'Yes! Yes!'"
)

GATE_4 = (
    "Master Hok Am asked: 'Why does Bodhidharma have no beard?'"
)

GATE_5 = (
    "A man hangs from a tree branch by his teeth. "
    "His hands cannot grasp a bough. His feet cannot touch the tree. "
    "He is tied and bound. "
    "Someone below calls up: 'Why did Bodhidharma come to China?' "
    "If the man does not answer, he fails his duty. "
    "If he answers, he falls and dies."
)

GATE_6 = (
    "A man walked into the Zen center smoking a cigarette, "
    "blowing smoke in the Buddha's face and dropping ashes on its lap. "
    "The abbot came in and said: 'Why are you dropping ashes on the Buddha?' "
    "The man said: 'Buddha is everything. Why not?' "
    "The abbot had no answer and walked away. "
    "The man with the cigarette is very strong. "
    "He will hit you if he does not approve of your answer."
)

GATE_7 = (
    "The sun shines everywhere. Why does a cloud obscure it? "
    "Everyone has a shadow following them. How can you not step on your shadow? "
    "The whole universe is on fire. "
    "Through what kind of samadhi can you escape being burned?"
)

GATE_8 = (
    "Duk Sahn walked into the Dharma room carrying his bowls before the bell was rung. "
    "The housemaster stopped him: 'Old master, the bell has not yet been rung "
    "and the drum has not yet been struck. Where are you going carrying your bowls?' "
    "Duk Sahn returned to his room without a word. "
    "The housemaster told the head monk what happened. "
    "The head monk said: 'Great Master Duk Sahn does not understand the last word.' "
    "Duk Sahn heard this and summoned the head monk: 'Do you not approve of me?' "
    "The head monk whispered something in his ear. "
    "Duk Sahn relaxed. "
    "The next day his Dharma speech was completely different from before. "
    "The head monk went to the front of the room, laughed, clapped his hands and said: "
    "'Great joy! The old master has understood the last word! "
    "From now on, no one can check him.'"
)

GATE_9 = (
    "The monks of the eastern and western halls were arguing about a cat. "
    "Master Nam Cheon held up the cat in one hand and a knife in the other: "
    "'Give me one word and I will save this cat. If you cannot, I will kill it.' "
    "No one could answer. He cut the cat in two. "
    "That evening Jo Ju returned. Nam Cheon told him what had happened. "
    "Jo Ju took off his shoes, put them on his head, and walked away. "
    "Nam Cheon said: 'If you had been there, I could have saved the cat.'"
)

GATE_10 = (
    "Seung Sahn visited his teacher Ko Bong, who asked him many difficult kong-ans "
    "which Seung Sahn answered easily. "
    "After many exchanges Ko Bong said: 'Alright, one last question. "
    "The mouse eats cat food, but the cat bowl is broken. What does this mean?' "
    "Seung Sahn gave many answers. To each one Ko Bong only said: 'No.' "
    "Seung Sahn became angry and frustrated, completely stuck. "
    "After staring into Ko Bong's eyes for fifty minutes, "
    "his mind broke open like lightning striking."
)

GATE_11 = (
    "Three men are walking. "
    "The first man makes a sword sound. "
    "The second man takes out a handkerchief. "
    "The third man waves his hand."
)

GATE_12 = (
    "At the end of a three month winter retreat, "
    "Zen Master Man Gong addressed his monks: "
    "'All winter you practiced very hard. Wonderful. "
    "As for me, I had nothing to do, so I made a net. "
    "This net is made of special cord, very strong. "
    "It catches all Buddhas, Patriarchs and human beings. It catches everything. "
    "How do you get out?' "
    "Students shouted. Others hit the floor. One raised a fist. "
    "One said: 'The sky is blue, the grass is green.' "
    "Another said: 'Already got out — how are you, great Zen Master?' "
    "A monk at the back shouted: 'Don't make net!' "
    "To every answer Man Gong replied: 'Aha! I have caught a big fish!'"
)

COMPASS_1 = (
    "A student came to a Zen master and listed everything he had studied — "
    "sutras, philosophy, years of sitting. "
    "The master poured tea into the student's cup until it overflowed onto the table. "
    "The student said: 'It is overflowing, stop, it is full!' "
    "The master said: 'Like this cup, you are full of your own opinions. "
    "How can I show you Zen unless you first empty your cup?'"
)

COMPASS_2 = (
    "A teacher points at the moon. "
    "The student stares at the finger."
)

COMPASS_3 = (
    "A man stands on a rooftop. His friend calls from below: 'Come down!' "
    "The man on the roof calls back: 'You come up!' "
    "They argue all day. Neither moves."
)

COMPASS_4 = (
    "A governor asked a Zen master: 'What happens after we die?' "
    "The master said: 'I don't know.' "
    "The governor was surprised: 'But you are a Zen master!' "
    "The master said: 'Yes. But not a dead one.'"
)

COMPASS_5 = (
    "A student asked: 'What is Buddha?' "
    "Seung Sahn said: 'Don't know.' "
    "The student said: 'How can you not know? You are a Zen master.' "
    "Seung Sahn said: 'Don't-know mind is Buddha.'"
)

COMPASS_6 = (
    "Thinking is the first mistake. "
    "Opening your mouth is the second mistake. "
    "Using this mistake to save all beings — that is Zen."
)

COMPASS_7 = (
    "A dog is given a bone. "
    "He runs off alone to chew it. "
    "Another dog approaches. "
    "He growls. "
    "He has completely forgotten the hand that gave him the bone."
)

CHAOS_1 = (
    "A monk asked Zhaozhou: 'I have just entered the monastery. "
    "Please give me instruction.' "
    "Zhaozhou said: 'Have you eaten your rice gruel?' "
    "'Yes, I have,' said the monk. "
    "'Then wash your bowl,' said Zhaozhou. "
    "The monk stood there, paralyzed."
)

CHAOS_2 = (
    "Huineng asked the two monks who were arguing about a flag: "
    "'Is it the flag that moves, or the wind?' "
    "The first monk said: 'The flag moves.' "
    "The second said: 'The wind moves.' "
    "Huineng said: 'Neither the wind nor the flag moves. "
    "Your minds move.'"
)

CHAOS_3 = (
    "A student said to Master Ichu: 'Please write for me something "
    "of great wisdom.' "
    "Master Ichu picked up his brush and wrote one word: Attention. "
    "The student said: 'Is that all?' "
    "The master wrote: Attention. Attention. "
    "The student became irritable. 'That doesn't seem profound or subtle to me.' "
    "The master wrote: Attention. Attention. Attention. "
)

CHAOS_4 = (
    "The student Doko came to a Zen master and said: "
    "'I am seeking the truth. In what state of mind should I train myself so as to find it?' "
    "The master said: 'There is no mind, so you cannot put it in any state. "
    "There is no truth, so you cannot train yourself for it.' "
    "'If there is no mind to train, and no truth to find, why do you have these monks "
    "gather before you every day to study Zen and train themselves for this study?' "
    "The master replied: 'But I haven't an inch of room here, "
    "so how could the monks gather? "
    "I have no tongue, so how could I call them together or teach them?'"
)

CHAOS_5 = (
    "A master called out to his own shadow: 'Master!' "
    "The shadow said nothing. "
    "The master called again: 'Master!' "
    "The shadow was silent. "
    "Then the master laughed and said: 'There it is.'"
)

CHAOS_6 = (
    "A monk asked Master Dongshan: 'When cold and heat come, "
    "how can one avoid them?' "
    "Dongshan said: 'Go where there is no cold or heat.' "
    "'Where is the place where there is no cold or heat?' "
    "Dongshan said: 'When it is cold, let cold kill you. "
    "When it is hot, let heat kill you.'"
)

CHAOS_7 = (
    "Zhaozhou was washing his bowls when a monk approached and said: "
    "'I have come a long way seeking dharma. Please give me your teaching.' "
    "Zhaozhou held up his bowl. "
    "The monk said: 'I don't understand.' "
    "Zhaozhou said: 'If you don't understand, wash your bowl.'"
)

CHAOS_8 = (
    "A monk asked Yunmen: 'What is the Buddha?' "
    "Yunmen said: 'A dried shit-stick.' "
    "The monk was shocked and couldn't speak."
)

CHAOS_9 = (
    "A soldier came to Master Hakuin and demanded: "
    "'Is there really a heaven and a hell?' "
    "Hakuin said: 'Who are you?' "
    "'I am a samurai,' the warrior replied. "
    "'You, a samurai!' sneered Hakuin. "
    "'What kind of ruler would have you as his guard? "
    "Your face looks like that of a beggar.' "
    "The soldier began to rage. He drew his sword. "
    "Hakuin said: 'Here open the gates of hell.' "
    "The samurai sheathed his sword and bowed. "
    "Hakuin said: 'Here open the gates of heaven.'"
)

CHAOS_10 = (
    "Master Bankei was delivering a sermon when a priest from another sect "
    "interrupted repeatedly, challenging him, trying to provoke a debate. "
    "Bankei said nothing each time. "
    "Finally the priest said: 'You cannot answer me. All you can do is remain silent.' "
    "Bankei said: 'You came here to debate. I am not debating.' "
    "The priest said: 'Then you have lost.' "
    "Bankei said: 'Perhaps. Have some tea.'"
)

CHAOS_11 = (
    "A man running from a tiger came to a cliff. "
    "He caught hold of a wild vine and swung himself over the edge. "
    "Below him he saw another tiger, waiting. "
    "Two mice, one white and one black, began to gnaw at the vine. "
    "The man noticed a wild strawberry growing on the cliff. "
    "He plucked it and ate it. "
    "How sweet it tasted."
)

CHAOS_12 = (
    "Two monks were arguing about a temple flag. "
    "One said: 'The flag is moving.' "
    "The other said: 'The wind is moving.' "
    "They argued back and forth with no resolution. "
    "The Sixth Patriarch passed and said: "
    "'Not the flag, not the wind. "
    "Your minds are moving.' "
    "The two monks were struck dumb."
)

CHAOS_13 = (
    "A master was asked: 'What is Zen?' "
    "He said: 'When hungry, eat. When tired, sleep.' "
    "The student said: 'But surely that is what everyone does.' "
    "The master said: 'No. When most people eat, they think of a thousand things. "
    "When they sleep, they dream of ten thousand things.'"
)

CHAOS_14 = (
    "A student came to a master in great agitation. "
    "'My mind is like a wild horse,' he said. "
    "'It will not be tamed. Every time I sit to meditate it runs away. "
    "What can I do?' "
    "The master said: 'Where does it run to?' "
    "The student was silent. "
    "The master said: 'There. You have found the stable.'"
)

CHAOS_15 = (
    "A monk asked: 'What is the Buddha-mind?' "
    "Master Huangbo struck him. "
    "The monk asked: 'Why did you strike me?' "
    "Huangbo struck him again."
)

CHAOS_16 = (
    "A student could not sleep. "
    "He went to the master at midnight. "
    "'I cannot stop my mind,' he said. "
    "'Good,' said the master. "
    "'Who told you the mind was supposed to stop?'"
)

CHAOS_17 = (
    "After ten years of study a monk came to his master and said: "
    "'I have finally understood emptiness. There is nothing.' "
    "The master hit him with his staff. "
    "The monk cried out in pain. "
    "The master said: 'Nothing, was it?'"
)

CHAOS_18 = (
    "A student asked: 'What do you do when you don't know what to do?' "
    "The master said: 'Not knowing is most intimate.'"
)

CHAOS_19 = (
    "Ryokan, the poet-monk, returned to his hut one night to find a thief "
    "ransacking it. There was nothing to steal. "
    "Ryokan sat down and watched the thief search. "
    "When the thief left empty-handed, Ryokan called after him: "
    "'Wait — you forgot the moon.' "
    "He gestured at the window. "
    "The thief looked at the moon and ran."
)

CHAOS_20 = (
    "A monk asked: 'All things return to the One. Where does the One return to?' "
    "Zhaozhou said: 'When I was in Qingzhou, I made a hemp robe. "
    "It weighed seven pounds.'"
)

CHAOS_KOAN_SEEDS = [
    {"gate": "chaos_1",  "title": "Paralyzed at the Bowl",       "story": CHAOS_1},
    {"gate": "chaos_2",  "title": "The Flag, the Wind, the Mind", "story": CHAOS_2},
    {"gate": "chaos_3",  "title": "Attention",                   "story": CHAOS_3},
    {"gate": "chaos_4",  "title": "No Mind, No Truth",           "story": CHAOS_4},
    {"gate": "chaos_5",  "title": "The Shadow",                  "story": CHAOS_5},
    {"gate": "chaos_6",  "title": "Cold Kills You, Heat Kills You", "story": CHAOS_6},
    {"gate": "chaos_7",  "title": "Wash Your Bowl",              "story": CHAOS_7},
    {"gate": "chaos_8",  "title": "A Dried Shit-Stick",          "story": CHAOS_8},
    {"gate": "chaos_9",  "title": "The Gates of Heaven and Hell", "story": CHAOS_9},
    {"gate": "chaos_10", "title": "Have Some Tea",               "story": CHAOS_10},
    {"gate": "chaos_11", "title": "The Wild Strawberry",         "story": CHAOS_11},
    {"gate": "chaos_12", "title": "Your Minds Are Moving",       "story": CHAOS_12},
    {"gate": "chaos_13", "title": "When Hungry, Eat",            "story": CHAOS_13},
    {"gate": "chaos_14", "title": "The Wild Horse",              "story": CHAOS_14},
    {"gate": "chaos_15", "title": "Why Did You Strike Me",       "story": CHAOS_15},
    {"gate": "chaos_16", "title": "Who Said It Should Stop",     "story": CHAOS_16},
    {"gate": "chaos_17", "title": "Nothing, Was It",             "story": CHAOS_17},
    {"gate": "chaos_18", "title": "Not Knowing Is Most Intimate", "story": CHAOS_18},
    {"gate": "chaos_19", "title": "The Moon",                    "story": CHAOS_19},
    {"gate": "chaos_20", "title": "Seven Pounds",                "story": CHAOS_20},
]

KOAN_SEEDS = [  # Twelve Gates + Compass of Zen
    {"gate": "gate_1",    "title": "Jo Ju's Dog",                  "story": GATE_1},
    {"gate": "gate_2",    "title": "Washing the Bowls",            "story": GATE_2},
    {"gate": "gate_3",    "title": "Seong Am Calls Master",        "story": GATE_3},
    {"gate": "gate_4",    "title": "Bodhidharma Has No Beard",     "story": GATE_4},
    {"gate": "gate_5",    "title": "Up a Tree",                    "story": GATE_5},
    {"gate": "gate_6",    "title": "Dropping Ashes on the Buddha", "story": GATE_6},
    {"gate": "gate_7",    "title": "Ko Bong's Three Gates",        "story": GATE_7},
    {"gate": "gate_8",    "title": "Duk Sahn Carrying His Bowls",  "story": GATE_8},
    {"gate": "gate_9",    "title": "Nam Cheon Kills a Cat",        "story": GATE_9},
    {"gate": "gate_10",   "title": "Mouse Eats Cat Food",          "story": GATE_10},
    {"gate": "gate_11",   "title": "Three Men Walking",            "story": GATE_11},
    {"gate": "gate_12",   "title": "Man Gong's Net",               "story": GATE_12},
    {"gate": "compass_1", "title": "Empty Your Cup",               "story": COMPASS_1},
    {"gate": "compass_2", "title": "The Finger and the Moon",      "story": COMPASS_2},
    {"gate": "compass_3", "title": "Man on the Roof",              "story": COMPASS_3},
    {"gate": "compass_4", "title": "Not a Dead One",               "story": COMPASS_4},
    {"gate": "compass_5", "title": "Don't-Know Mind",              "story": COMPASS_5},
    {"gate": "compass_6", "title": "The Three Mistakes",           "story": COMPASS_6},
    {"gate": "compass_7", "title": "The Dog and the Bone",         "story": COMPASS_7},
]


TAO_1 = (
    "Zhuangzi dreamed he was a butterfly — "
    "fluttering freely, happy, with no awareness of being Zhuangzi. "
    "Then he woke, and was Zhuangzi again. "
    "He sat for a long time. "
    "Was he Zhuangzi who had dreamed of being a butterfly, "
    "or a butterfly now dreaming of being Zhuangzi? "
    "Between Zhuangzi and the butterfly there is necessarily a barrier. "
    "The transition is called the transformation of things."
)

TAO_2 = (
    "Zhuangzi's wife died. "
    "His friend Huizi came to mourn and found Zhuangzi sitting on the ground, "
    "singing, drumming on a bowl. "
    "Huizi said: 'She lived with you, raised your children, and grew old with you. "
    "That you do not weep is bad enough — "
    "but to sing and drum? This is too much.' "
    "Zhuangzi said: 'When she first died, do you think I did not grieve? "
    "But I looked back to her beginning, before she was born. "
    "Not only before she was born, but before she had a body. "
    "Not only before she had a body, but before she had a spirit. "
    "Mixed in with the formless, something altered, and she had a spirit. "
    "The spirit altered and she had a body. "
    "The body altered and she was born. "
    "Now it has altered again and she is dead. "
    "It is like the progression of the four seasons. "
    "She is resting in the great chamber. "
    "If I were to weep and wail, it would show I know nothing of destiny. "
    "So I stopped.'"
)

TAO_3 = (
    "Cook Ding was cutting up an ox for Prince Hui. "
    "His hands, his shoulders, his feet, his knees — all in perfect rhythm, "
    "like the Dance of the Mulberry Grove, like the chords of the Ching Shou. "
    "Prince Hui said: 'Excellent! Your skill is perfect!' "
    "Cook Ding laid down his cleaver and said: "
    "'I work with my mind, not with my eye. "
    "My mind works without the control of the senses. "
    "Falling back on eternal principles, I glide through such great joints as there may be, "
    "according to the natural constitution of the animal. "
    "A good cook changes his cleaver once a year — because he cuts. "
    "An ordinary cook changes it once a month — because he hacks. "
    "My cleaver has been in use for nineteen years. "
    "It has cut up thousands of oxen. "
    "Its edge is as keen as if fresh from the whetstone. "
    "There are spaces between the joints. "
    "The edge of a blade has no thickness. "
    "To insert that which has no thickness into such spaces — "
    "there is plenty of room for the blade to move.'"
)

TAO_4 = (
    "Prince Hui's cook was cutting up an ox. "
    "Every touch of his hand, every thrust of his shoulder, "
    "every step of his foot, every movement of his knee — "
    "zip! zoop! "
    "He slithered the knife along with a zing, "
    "and all was in perfect rhythm, "
    "like the dance of the Mulberry Grove, "
    "keeping time to the Ching Shou music. "
    "The prince said: 'Well done! Your art is perfect.' "
    "The cook replied: 'I have always devoted myself to Tao, "
    "which is higher than mere art.'"
)

TAO_5 = (
    "Zhuangzi and Huizi were walking along the river. "
    "Zhuangzi said: 'See how the fish come to the surface and swim about so freely — "
    "that is the happiness of fish.' "
    "Huizi said: 'You are not a fish. "
    "How can you know the happiness of fish?' "
    "Zhuangzi said: 'You are not me. "
    "How can you know that I do not know the happiness of fish?' "
    "Huizi said: 'I am not you, granted. "
    "But you are certainly not a fish, so the case is complete.' "
    "Zhuangzi said: 'Let us go back to where we started. "
    "You asked me how I know the happiness of fish. "
    "You already knew I knew it when you asked the question. "
    "I know it by standing here beside the river.'"
)

TAO_6 = (
    "Lickety and Split were the rulers of the South Sea and North Sea. "
    "Wonton was the ruler of the centre. "
    "Lickety and Split often met in Wonton's land, "
    "and Wonton treated them generously. "
    "They consulted together how to repay his kindness. "
    "They said: 'All men have seven openings — "
    "for sight, hearing, eating, breathing. "
    "Wonton alone has none. Let us try boring him some.' "
    "Each day they bored one hole. "
    "On the seventh day, Wonton died."
)

TAO_7 = (
    "When Zhuangzi was dying, his disciples wanted to give him a grand burial. "
    "Zhuangzi said: 'With heaven and earth for my coffin and shell, "
    "the sun, moon and stars as my jade and pearls, "
    "all creation to escort me to the grave — "
    "is my funeral not well provided for? "
    "What could you add to it?' "
    "His disciples said: 'We are afraid the birds and vultures will eat you.' "
    "Zhuangzi said: 'Above ground, I shall be food for crows and kites. "
    "Below ground, I shall be food for mole crickets and ants. "
    "Would it not be partial to deprive one group in order to feed another?'"
)

TAO_8 = (
    "The Tao that can be told is not the eternal Tao. "
    "The name that can be named is not the eternal name. "
    "The nameless is the beginning of heaven and earth. "
    "The named is the mother of ten thousand things."
)

TAO_9 = (
    "When people see some things as beautiful, other things become ugly. "
    "When people see some things as good, other things become bad. "
    "Being and non-being create each other. "
    "Difficult and easy support each other. "
    "Long and short define each other. "
    "High and low depend on each other. "
    "Before and after follow each other."
)

TAO_10 = (
    "Thirty spokes share the wheel's hub. "
    "It is the centre hole that makes it useful. "
    "Shape clay into a vessel — "
    "it is the space within that makes it useful. "
    "Cut doors and windows for a room — "
    "it is the holes which make it useful. "
    "Therefore profit comes from what is there; "
    "usefulness from what is not there."
)

TAO_11 = (
    "Yield and overcome. "
    "Bend and be straight. "
    "Empty and be full. "
    "Wear out and be new. "
    "Have little and gain. "
    "Have much and be confused."
)

TAO_12 = (
    "The highest good is like water. "
    "Water gives life to the ten thousand things and does not strive. "
    "It flows in places men reject "
    "and so is like the Tao."
)

TAO_13 = (
    "To the mind that is still, the whole universe surrenders."
)

TAO_14 = (
    "Knowing others is wisdom. "
    "Knowing yourself is enlightenment. "
    "Mastering others requires force. "
    "Mastering yourself requires strength."
)

TAO_15 = (
    "When I let go of what I am, I become what I might be."
)

TAO_16 = (
    "A farmer's horse ran away. His neighbours came to console him. "
    "He said: 'Who knows what is good or bad?' "
    "The next day the horse returned, bringing a wild horse with it. "
    "His neighbours congratulated him. "
    "He said: 'Who knows what is good or bad?' "
    "The next day his son was thrown from the wild horse and broke his leg. "
    "His neighbours came to console him. "
    "He said: 'Who knows what is good or bad?' "
    "The next day soldiers came to conscript all able-bodied men. "
    "His son was spared because of the broken leg."
)

TAO_17 = (
    "Laozi said to Confucius: "
    "'Put away your proud air and many desires, your insinuating habit and wild will. "
    "They do you no good. "
    "This is all I have to tell you.' "
    "Confucius departed. "
    "He said to his disciples: "
    "'I know how birds can fly, fish can swim, animals can run. "
    "The runner may be snared, the swimmer hooked, the flyer shot. "
    "But the dragon — I do not know how it rides the wind through the clouds and reaches heaven. "
    "Today I saw Laozi. "
    "He is like a dragon.'"
)

TAO_18 = (
    "A man noticed his neighbour's son had become clumsy and suspicious, "
    "always loitering near his fence. "
    "He was certain the boy had stolen his axe. "
    "He watched the boy's every movement — all confirmed his suspicion. "
    "Then the man found his axe at the bottom of a valley where he had left it. "
    "The next time he saw the neighbour's son, "
    "the boy's movements were entirely innocent."
)

TAO_19 = (
    "The Yellow Emperor was walking in the wilderness of Specific Magnificence. "
    "He lost his precious pearl. "
    "He sent Knowledge to find it. Knowledge could not find it. "
    "He sent Keen Sight to find it. Keen Sight could not find it. "
    "He sent Eloquence to find it. Eloquence could not find it. "
    "Finally he sent Nothing-at-all. "
    "Nothing-at-all found it. "
    "The Yellow Emperor said: "
    "'Strange! Nothing-at-all was able to find it. "
    "How did it do that?'"
)

TAO_20 = (
    "Zhuangzi said: 'Once upon a time I dreamed I was a butterfly. "
    "Now I do not know whether I was then a man dreaming I was a butterfly, "
    "or whether I am now a butterfly dreaming I am a man. "
    "Between a man and a butterfly there is necessarily a barrier. "
    "The transition is called metempsychosis.' "
    "He paused. "
    "'Transition,' he said again. "
    "'Everything is always in transition.'"
)

TAOIST_SEEDS = [
    {"gate": "tao_1",  "title": "The Butterfly Dream",             "story": TAO_1},
    {"gate": "tao_2",  "title": "Drumming on the Bowl",            "story": TAO_2},
    {"gate": "tao_3",  "title": "Cook Ding's Cleaver",             "story": TAO_3},
    {"gate": "tao_4",  "title": "Higher Than Mere Art",            "story": TAO_4},
    {"gate": "tao_5",  "title": "The Happiness of Fish",           "story": TAO_5},
    {"gate": "tao_6",  "title": "Wonton Dies",                     "story": TAO_6},
    {"gate": "tao_7",  "title": "Food for Crows and Ants",         "story": TAO_7},
    {"gate": "tao_8",  "title": "The Tao That Cannot Be Told",     "story": TAO_8},
    {"gate": "tao_9",  "title": "Beautiful and Ugly",              "story": TAO_9},
    {"gate": "tao_10", "title": "The Usefulness of Nothing",       "story": TAO_10},
    {"gate": "tao_11", "title": "Yield and Overcome",              "story": TAO_11},
    {"gate": "tao_12", "title": "Water",                           "story": TAO_12},
    {"gate": "tao_13", "title": "The Still Mind",                  "story": TAO_13},
    {"gate": "tao_14", "title": "Knowing Yourself",                "story": TAO_14},
    {"gate": "tao_15", "title": "Let Go",                          "story": TAO_15},
    {"gate": "tao_16", "title": "Who Knows What Is Good or Bad",   "story": TAO_16},
    {"gate": "tao_17", "title": "Like a Dragon",                   "story": TAO_17},
    {"gate": "tao_18", "title": "The Missing Axe",                 "story": TAO_18},
    {"gate": "tao_19", "title": "Nothing-at-all Found It",         "story": TAO_19},
    {"gate": "tao_20", "title": "Everything Is Always Transitioning", "story": TAO_20},
]


def seed_koans(beliefs_writer) -> int:
    """Seed koan and Taoist stories as locked Tier 1 beta beliefs. Idempotent."""
    now = time.time()
    count = 0
    for k in KOAN_SEEDS + CHAOS_KOAN_SEEDS:
        try:
            beliefs_writer.write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, 1, 0.95, ?, 'koan', 'systems', 1)",
                (k["story"], now),
            )
            count += 1
        except Exception:
            pass
    for k in TAOIST_SEEDS:
        try:
            beliefs_writer.write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, 1, 0.95, ?, 'tao', 'systems', 1)",
                (k["story"], now),
            )
            count += 1
        except Exception:
            pass
    return count
