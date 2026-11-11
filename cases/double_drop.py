"""Case 1: The Double Drop. Port Meridian, November 1947.

SOLUTION (spoilers): Dr. Lenora Voss killed Victor Halloran with injectable digoxin
slipped into his brandy flask between 10:11 and 10:15, while Webb fetched ice. Motive:
Victor's real ledger recorded her monthly payments for signing false death certificates
and he meant to hand it to the Inspector on Monday.

Timeline
  9:30  Webb fills the flask.            9:44  Voss reclaims her bag at the coat check.
  9:50  Voss examines Victor (Webb present); Victor: "Monday I go to the Inspector."
  9:55  Eleanor quarrels with Victor, burns her divorce petition.
 10:00  Vera visits; Victor tells her about "two drops". She leaves 10:10, sees Voss in the corridor.
 10:11  Webb sent for ice; Voss stays with Victor alone.   10:15  Photo: Voss's chair is empty.
 10:16  Voss hurries down the back stairs (Finch sees her).
 10:20  Finch visits; 10:25 Victor drinks, "bitter".  10:28  Finch leaves the real ledger at the coat check.
 10:35  Julian steals cash from the safe; Victor looks drunk.   10:46  Dray arrives.
 10:50  Webb hears the lock turn.   10:50 Finch drops the decoy at Pier 9.   11:00  Victor dies.
 11:40  Door broken in; Voss goes to the safe before the body.
"""
from quest import (Case, Character, Choice, Clue, Hint, Location, Reaction, Spot, Topic)

CLUES = (
    Clue("lab_report", "Coroner's report",
         "Dr. Pell at the morgue: death by digoxin, injectable grade. Tablets could never reach that concentration, "
         "so Victor's own heart pills are out. The heart stopped around eleven. He swallowed the dose between "
         "9:30 and 10:30, no later."),
    Clue("flask", "The silver flask",
         "Victor's flask, cap off, a little brandy left. It smells of brandy and, underneath, something sharp and "
         "bitter. Only Victor's prints, and Webb's smudged ones."),
    Clue("locked_study", "Locked from inside",
         "The study door was locked from inside and the key was in Victor's waistcoat. The window is latched. "
         "A locked room only matters if someone had to get out. Poison does not."),
    Clue("ash", "Burned divorce petition",
         "Fresh ash in the grate, one corner unburned: PETITION FOR DIVORCE, Eleanor Halloran, plaintiff. "
         "Someone burned it tonight."),
    Clue("safe_open", "Emptied safe",
         "The safe stands open, dial untouched. Two thousand dollars in cash is gone. No papers and no ledger, "
         "though there is a clean rectangle in the dust, the size of a bound book."),
    Clue("matchbook", "Blue Heron matchbook",
         "A matchbook from the Blue Heron Lounge on Fisher Street. Inside, in Victor's handwriting: ask for V."),
    Clue("lipstick_glass", "Lipstick on a glass",
         "A crystal glass rimmed in crimson lipstick, and warm perfume still in the sofa cushions. A woman sat "
         "here tonight, and not long ago."),
    Clue("ampule_shard", "Glass ampule shard",
         "A sliver of glass under the desk, with a paper label fragment: ...GOX... ST. ANS... A medical ampule, "
         "from St. Anselm's Hospital stock."),
    Clue("bitter_taste", "\"The brandy's turned\"",
         "Finch: at 10:25 Victor took a long pull from the flask, grimaced and said, \"Marcus's brandy is turning.\" "
         "So the poison was already in the flask by then."),
    Clue("ice_run", "Webb's four minutes",
         "Webb: at 10:11 Victor wanted ice for his brandy. Dr. Voss, who had appeared at the door, said she would "
         "stay with him. Webb was gone four minutes. When he returned she was packing her stethoscope."),
    Clue("ice_slip", "Kitchen ice slip",
         "A kitchen slip: Ice, 3F study, 10:11 pm, M. Webb. The night chef stamps everything. "
         "Webb's four minutes are real."),
    Clue("voss_claim", "Voss's account",
         "Dr. Voss says she examined Victor once, at 9:50, with Webb present, then went down to the ballroom and "
         "never left it. \"Ask four hundred guests.\""),
    Clue("vera_saw", "Vera saw the doctor",
         "Vera: as she left the study at ten past ten, Dr. Voss was waiting at the end of the corridor, bag in "
         "hand, and said she would \"look in on him.\" Victor had said nothing about a doctor."),
    Clue("service_stairs", "The back stairs, 10:16",
         "Finch: at 10:16 Dr. Voss came down the back stairs so fast she nearly knocked him over, her black bag "
         "clinking. \"He's resting. Don't disturb him.\""),
    Clue("two_drops", "\"Two drops tonight\"",
         "Vera: Victor said, \"Tonight I make two drops, Vera. One for the rats and one for the law.\" "
         "Two handovers of something, in one night."),
    Clue("coat_ticket", "Parcel for the Inspector",
         "Nell: at 10:28 Mr. Finch left a brown-paper parcel, marked For Inspector Calloway. Hold until she "
         "asks. Nell cannot release it without Calloway's say-so."),
    Clue("calloway_ok", "Calloway's authorization",
         "Calloway scribbles a note: release to bearer. It is the Inspector's authority to open the parcel."),
    Clue("real_ledger", "The real ledger",
         "Victor's ledger. Capt. M.R., $500 a month, harbor clearance. S.D., $1,200 a month, wholesale. "
         "And: Dr. V., $300 a month, certificates, six dock deaths 1946-47. The Inspector was meant to read "
         "this on Monday."),
    Clue("decoy_ledger", "The decoy ledger",
         "A bound book, blank except for the first page: a short list naming only Reyes and Dray. Bait. "
         "Victor wanted to see who came for it."),
    Clue("finch_courier", "Finch's two parcels",
         "Finch: Victor gave him two parcels. The real ledger to Nell's counter for the Inspector, the decoy to "
         "Pier 9 for whoever was watching. \"Two drops, Tobias, and nobody knows which is real.\""),
    Clue("reyes_car", "Packard tracks, Pier 9",
         "Fresh tire tracks on the wet planks, wide wheelbase, a Packard. The harbor master's car."),
    Clue("photo_1015", "Gala photograph, 10:15",
         "The gala photographer's plate, stamped 10:15: Captain Reyes on the stage taking his award. In the "
         "foreground, Table 4, the hospital board. One chair empty: Dr. L. Voss. Her black bag is gone from "
         "under it."),
    Clue("dray_late", "Dray arrived at 10:46",
         "The doorman's log: S. Dray, Blue Heron, 10:46 pm. He walked in an hour after the poison went into "
         "the flask."),
    Clue("dray_goods", "Dray's stock book",
         "Dray's back-office book lists whiskey, nylons, cigarettes and black-market penicillin. Nothing "
         "hospital-grade that could kill by injection."),
    Clue("bag_ticket", "Voss's bag, 9:44",
         "Nell's ticket book: Dr. L. Voss, black bag, reclaimed 9:44 pm. Nell's note: never takes it to the "
         "ballroom. Odd."),
    Clue("julian_saw", "Julian in the study",
         "Julian: at 10:35 he found his father slumped in the armchair, flushed and sweating. He thought it "
         "was brandy, took the cash and left. The flask was on the desk, cap on."),
    Clue("foxglove", "Eleanor's foxglove",
         "Foxglove in the winter garden, the plant digitalis comes from. All the pots are intact, the soil "
         "undisturbed. A tempting suspect, and a dead end."),
    Clue("eleanor_quarrel", "Eleanor's quarrel",
         "Eleanor: at five to ten Victor told her, \"Monday I fix everything, Eleanor, including you.\" "
         "She burned the petition after he refused to talk. Four minutes in the room, she says, and she "
         "never touched a thing."),
    Clue("monday_threat", "\"Monday, Lenora\"",
         "Webb overheard the 9:50 exam. Victor to the doctor: \"Monday I go to the Inspector, Lenora. All of "
         "it, with your name in it. I am sorry.\" She went white. Webb thought he meant her fees."),
    Clue("deposit_slips", "Deposit slips, $300",
         "Bank slips in Voss's desk: $300 every month from H.S.T. Co., Halloran Shipping and Trading. They "
         "match the Dr. V. entries in the ledger, to the month."),
    Clue("ampule_log", "Ampule inventory",
         "Voss's locked cabinet: her log shows ten ampules of St. Anselm digoxin; eight are in the tray. "
         "Two are gone, and the tray label matches the shard from the study."),
)

LOCATIONS = (
    Location(
        "lobby", "Grand Lobby",
        "The lobby of the Meridian Grand Hotel: marble, brass, and a puddle spreading under every umbrella. "
        "Officers keep the guests behind a rope. Nell Archer watches it all from the coat-check counter.",
        spots=(
            Spot("coat_check", "Coat-check counter",
                 "Rows of wet coats. Nell's carbon ticket book lies open on the counter. Entry, 9:44 pm: "
                 "Dr. L. Voss, black bag, RECLAIMED. Beside it, Nell's pencilled note: never takes it up to the "
                 "ballroom. Odd.", gives=("bag_ticket",)),
            Spot("doorman", "Doorman's arrival log",
                 "The doorman's log, in a neat hand. S. Dray, Blue Heron, 10:46 pm. Dray walked in long after "
                 "Victor had left the ballroom.", gives=("dray_late",)),
        ),
        people=("nell",),
    ),
    Location(
        "study", "Halloran's Study",
        "Third floor, east wing: oak panelling, a banked fireplace, a cold cigar in a crystal ashtray. "
        "No chalk outline, just the armchair where he died, still dented.",
        spots=(
            Spot("door", "The door and window",
                 "The door was broken in at 11:40, the lock splintered from inside. Victor's key was in his "
                 "waistcoat and the window is latched. A locked room, but a locked room only matters if someone "
                 "had to get out. Whatever killed him may have been in the room already.",
                 gives=("locked_study",)),
            Spot("desk", "The desk",
                 "On the blotter: Victor's silver flask, cap off, a little brandy left. It smells of brandy and, "
                 "underneath, something sharp and bitter. Only Victor's prints, and Webb's smudged ones.",
                 gives=("flask",)),
            Spot("ashtray", "The ashtray",
                 "Under the cold cigar, a matchbook with a blue heron on the cover: the Blue Heron Lounge, "
                 "Fisher Street. Inside, in Victor's hand: ask for V.", gives=("matchbook",)),
            Spot("fireplace", "The fireplace",
                 "Fresh ash in the grate, one corner unburned: PETITION FOR DIVORCE, Eleanor Halloran, "
                 "plaintiff. Someone burned it tonight.", gives=("ash",)),
            Spot("safe", "The wall safe",
                 "The safe stands open, dial untouched. Two thousand dollars in cash is gone. No papers, no "
                 "ledger, though there is a clean rectangle in the dust, the size of a bound book.",
                 gives=("safe_open",)),
            Spot("sofa", "The sofa and side table",
                 "A cut-crystal glass on the side table, rimmed in crimson lipstick. Warm perfume still in the "
                 "cushions. A woman sat here tonight.", gives=("lipstick_glass",)),
            Spot("rug", "Under the rug",
                 "On hands and knees, you find it by the desk leg: a sliver of glass with a paper label, "
                 "...GOX... ST. ANS... A medical ampule from St. Anselm's Hospital stock.",
                 gives=("ampule_shard",), requires=("lab_report",),
                 locked_hint="Not yet. You do not know what you are looking for. The coroner might."),
        ),
    ),
    Location(
        "ballroom", "The Ballroom",
        "A ghost party: champagne going flat, a band playing softly because nobody told them to stop. "
        "The guests murmur in clumps. The family has been herded under the chandelier.",
        spots=(
            Spot("terrace", "The winter garden",
                 "Eleanor's foxglove, potted along the glass: the plant digitalis comes from. Every pot is "
                 "intact, the soil undisturbed under a film of dust. A tempting suspect, and a dead end.",
                 gives=("foxglove",)),
            Spot("photographer", "The gala photographer",
                 "\"Table 4, ten-fifteen? Sure.\" He thumbs through his plates. At 10:15 the camera caught "
                 "Captain Reyes taking his award. In the foreground, the hospital board's table: one chair "
                 "empty, Dr. L. Voss, and her black bag is gone from under it.",
                 gives=("photo_1015",), requires=("voss_claim",),
                 locked_hint="The photographer is shooting the whole room. You would need a reason to ask about a "
                             "specific moment, and a specific person."),
        ),
        people=("eleanor", "julian", "voss", "reyes"),
    ),
    Location(
        "kitchen", "Service Corridor and Kitchen",
        "Steam, clattering pans, the smell of onions and wet wool. Staff whisper in three languages. A narrow "
        "back staircase climbs to the upper floors.",
        spots=(
            Spot("ice_slip", "The order spike",
                 "A slip on the spike: Ice, 3F study, 10:11 pm, M. Webb. The night chef stamps everything. "
                 "Webb's four minutes upstairs are real.", gives=("ice_slip",)),
        ),
        people=("webb", "finch"),
    ),
    Location(
        "heron", "Blue Heron Lounge",
        "Fisher Street. Smoke, a trio on the stage, a bartender who has seen everything and forgotten most of it. "
        "Silas Dray holds the corner booth. Vera Lane is warming up at the piano.",
        spots=(
            Spot("backoffice", "Dray's back office",
                 "The bartender looks away while you look at the stock book. Whiskey, nylons, cigarettes, "
                 "black-market penicillin. Nothing hospital-grade that could kill by injection.",
                 gives=("dray_goods",)),
        ),
        people=("vera", "dray"),
        requires=("matchbook",),
    ),
    Location(
        "pier9", "Pier 9",
        "One in the morning. Rain hammers the tin roof of an empty shed. A lantern swings on a bollard. "
        "This is where the second drop was supposed to end.",
        spots=(
            Spot("bollard", "The bollard",
                 "A bound book, wrapped in oilcloth and left where anyone could find it. Blank, except for the "
                 "first page: a short list naming only Reyes and Dray. Bait. Victor wanted to see who came.",
                 gives=("decoy_ledger",)),
            Spot("tracks", "The planks",
                 "Fresh tire tracks on the wet planks, a wide wheelbase. A Packard, the kind the harbor "
                 "master drives.", gives=("reyes_car",)),
        ),
        requires=("two_drops",),
    ),
    Location(
        "clinic", "Dr. Voss's Clinic",
        "Dock Street. Calloway's patrolman lets you in on a warrant signed by a half-asleep judge. White tile, "
        "carbolic, a locked glass cabinet and a roll-top desk.",
        spots=(
            Spot("cabinet", "The drug cabinet",
                 "Voss's inventory log lists ten ampules of St. Anselm digoxin. Eight sit in the tray. Two are "
                 "gone, and the tray's label matches the shard from the study.", gives=("ampule_log",)),
            Spot("rolltop", "The roll-top desk",
                 "A drawer of bank slips: $300 every month from H.S.T. Co., Halloran Shipping and Trading. "
                 "They match the Dr. V. entries in the real ledger, to the month.",
                 gives=("deposit_slips",)),
        ),
        requires=("real_ledger",),
    ),
)

CHARACTERS = (
    Character(
        "calloway", "Inspector Ruth Calloway", "Port Meridian PD",
        "Gray coat, gray eyes, a cigarette she never lights. Calloway cannot work this case officially, "
        "and everyone in the room knows it.",
        topics=(
            Topic("coroner", "The coroner's report",
                  "\"Pell rushed it for me. Digoxin, and not from any pill bottle. Injectable. He swallowed "
                  "it between nine-thirty and ten-thirty, then his heart quit around eleven. So the killer was "
                  "close to him before ten-thirty, not at midnight.\"", gives=("lab_report",)),
            Topic("access", "Who was near him tonight?",
                  "\"His wife, his son, his valet, his doctor, his mistress, his secretary. And two men who "
                  "owed him, or he owed them: Dray, the harbor master. Eight people, Detective, and most of "
                  "them lie before breakfast.\"", requires=("lab_report",)),
            Topic("parcel", "A parcel for the Inspector",
                  "Calloway goes very still. \"Victor told me on Thursday a parcel would reach me if anything "
                  "happened. I assumed he meant a letter.\" She writes something on a card. \"Take this to "
                  "whoever is holding it.\"", requires=("coat_ticket",), gives=("calloway_ok",)),
            Topic("ledger", "Read the ledger together",
                  "She reads for a long minute. \"Reyes. Dray. And here: Dr. V., certificates, six dock deaths "
                  "filed as accidents. There was exactly one doctor under that roof tonight.\" She stops. "
                  "\"Her clinic is on Dock Street. I will have a patrolman meet you with a warrant.\"",
                  requires=("real_ledger",)),
            Topic("ready", "Am I ready to accuse?",
                  "\"Tell me how he died, tell me why, and tell me who. If any of the three is a guess, "
                  "the DA will eat us both.\"", requires=("deposit_slips", "ampule_log")),
        ),
    ),
    Character(
        "nell", "Nell Archer", "Coat-check girl",
        "Nineteen, ink on her fingers, and a memory like a vault. She has been handing out wet coats since six "
        "and nobody has asked her a single question.",
        topics=(
            Topic("who", "Who came and went tonight?",
                  "\"Everyone, in their best. The harbor master first, at nine-twenty, then the family, then "
                  "the doctors from St. Anselm. The hospital board always comes in a pack. Mr. Dray came in "
                  "late. The doorman writes it all down, sir or ma'am.\""),
            Topic("parcel", "Did anyone leave anything for the Inspector?",
                  "She goes pale. \"At 10:28 Mr. Finch left a parcel in brown paper, marked For Inspector "
                  "Calloway, hold until she asks. I did not like how fast he ran off. I can't release it "
                  "without her say-so.\"", requires=("two_drops",), gives=("coat_ticket",)),
            Topic("release", "Release the parcel",
                  "Nell reads Calloway's card twice and hands over the parcel. Inside: a leather-bound ledger "
                  "in Victor's tight handwriting. Capt. M.R., $500 a month, harbor clearance. S.D., $1,200, "
                  "wholesale. Dr. V., $300 a month, certificates, six dock deaths 1946-47.",
                  requires=("calloway_ok",), gives=("real_ledger",)),
        ),
        reactions=(
            Reaction("real_ledger", "\"I never looked inside. I am so glad I never looked.\""),
        ),
        default_reaction="\"Nothing to do with the coats, so I wouldn't know.\"",
    ),
    Character(
        "eleanor", "Eleanor Halloran", "The widow",
        "Fifty, silk, and composed in a way that suggests rehearsal. She holds a champagne flute like a "
        "weapon she has no intention of using.",
        topics=(
            Topic("tonight", "Where were you tonight?",
                  "\"At my husband's side for the toasts, until I went up to see him about the seating chart "
                  "at five to ten. A few minutes. Then back to my guests. I do not carry poison in my "
                  "evening bag.\""),
            Topic("foxglove", "The foxglove in the winter garden",
                  "\"The florist's idea, not mine. Test every pot, Detective. I have not touched one in years.\"",
                  requires=("foxglove",)),
        ),
        reactions=(
            Reaction("ash",
                     "Her composure cracks. \"All right. There was no seating chart. I went up with the petition "
                     "and asked him to withdraw it. He laughed and said, 'Monday I fix everything, Eleanor, "
                     "including you.' I burned it in front of him. Four minutes, and I never touched a thing. "
                     "I do not know where he kept his brandy.\"", gives=("eleanor_quarrel",)),
            Reaction("foxglove", "\"Then you know it is only a plant. A pretty one.\""),
        ),
    ),
    Character(
        "julian", "Julian Halloran", "The son",
        "Twenty-seven, tuxedo rumpled, hands that can't find a pocket. Julian drinks like a man trying "
        "to forget a number.",
        topics=(
            Topic("tonight", "Where were you tonight?",
                  "\"Card room, all night, with the Ostrander brothers. Ask them.\" He does not look at you "
                  "when he says it."),
            Topic("dray", "Your debt to Silas Dray",
                  "\"Four thousand. Dad was going to pay it, or not. Dray is a creditor, not a murderer. A "
                  "dead father means no money for him. Or me.\"", requires=("julian_saw",)),
        ),
        reactions=(
            Reaction("safe_open",
                     "He folds. \"Two thousand. I owe Dray. I went up at half past ten. Dad was slumped in the "
                     "armchair, red in the face, sweating. I thought he was drunk. The flask was on the desk, cap "
                     "on. I took the cash and left. Oh God, he was dying and I took his money.\"",
                     gives=("julian_saw",)),
        ),
    ),
    Character(
        "webb", "Marcus Webb", "Halloran's valet",
        "Sixty, silver hair, shoes polished to a mirror shine despite the hour. Thirty years in the family's "
        "service. His eyes are red.",
        topics=(
            Topic("flask", "The flask",
                  "\"I fill it from the decanter every night at half past nine. Mr. Halloran takes one long "
                  "pull before he sleeps, never before. Nobody else touches that flask. Nobody.\" He says it "
                  "like a vow."),
            Topic("ice", "Did you leave him alone tonight?",
                  "\"Once. At eleven past ten Mr. Halloran wanted ice for his brandy. Dr. Voss had come to the "
                  "door for a quick recheck of his heart and said she would sit with him. I was gone four "
                  "minutes. When I got back she was putting away her stethoscope. 'Resting beautifully,' "
                  "she said.\"", requires=("flask",), gives=("ice_run",)),
            Topic("lock", "The locked door",
                  "\"At ten to eleven I passed and heard the key turn. 'Leave me be, Marcus,' he called. I broke "
                  "the door at 11:40 with the doctor beside me. She didn't kneel to his wrist, Detective. She "
                  "looked at the open safe first. I put it down to shock.\"", requires=("locked_study",)),
            Topic("monday", "What did Victor say at the 9:50 exam?",
                  "He hesitates. \"I was holding the doctor's bag. Mr. Halloran said, 'Monday I go to the "
                  "Inspector, Lenora. All of it, with your name in it. I am sorry.' She went white as the "
                  "sheets. I thought he meant her fees.\"", requires=("real_ledger",), gives=("monday_threat",)),
        ),
        reactions=(
            Reaction("ice_slip", "\"Ten-eleven. The chef stamps everything, sir or ma'am.\""),
            Reaction("julian_saw", "He closes his eyes. \"Master Julian, with his father dying in the chair. "
                                   "Don't tell the mistress, I beg you.\""),
        ),
    ),
    Character(
        "voss", "Dr. Lenora Voss", "Family physician",
        "Fifty, a physician's calm and a black bag she keeps within reach. She has been comforting people "
        "all night. Her hands are perfectly steady.",
        topics=(
            Topic("exam", "Your examination of Halloran",
                  "\"I examined Victor once, at ten to ten, with Marcus in the room. His pulse was fair for his "
                  "age. Then I went down to the ballroom and did not leave it until the news came. Ask four "
                  "hundred guests.\"", gives=("voss_claim",)),
            Topic("others", "Who else could have done this?",
                  "\"Look at the harbor. Men like Dray have hospital stock by the crate. And the family, of "
                  "course. Money makes strangers of people.\" She sips her water.", requires=("lab_report",)),
            Topic("ampules", "About that St. Anselm ampule",
                  "\"St. Anselm supplies every clinic from here to the docks. Glass proves a hospital exists, "
                  "Detective, nothing more.\" Her hands do not move.", requires=("ampule_shard",)),
        ),
        reactions=(
            Reaction("ice_run", "\"Marcus is old and confused about the time. I stopped by at ten for thirty "
                                "seconds, to ask whether he had taken his pills.\" A flicker, then it is gone."),
            Reaction("vera_saw", "\"A singer's word against a physician's? I was in the powder room, "
                                 "Detective, like half the ladies tonight.\""),
            Reaction("service_stairs", "\"A secretary who scurries down back stairs and sees what he likes. "
                                       "Wrong person. Wrong stairs.\""),
            Reaction("photo_1015", "\"I was in the powder room. A woman is allowed one.\""),
            Reaction("bag_ticket", "\"I like my bag with me. A doctor is never off duty.\""),
            Reaction("real_ledger", "She is quiet for a very long moment. \"Do you know what that book would do to "
                                    "this city? Nothing in it puts a needle in my hand.\""),
            Reaction("monday_threat", "\"Victor said many things on Mondays. He was a dramatic man, and "
                                      "he is dead.\" The water glass trembles."),
            Reaction("deposit_slips", "\"Consulting fees. Quite legal.\" Her voice is very thin."),
            Reaction("ampule_log", "She says nothing at all. Then, softly: \"I would like my lawyer.\""),
        ),
        default_reaction="\"I do not see what that has to do with a heart condition.\"",
    ),
    Character(
        "reyes", "Captain Mateo Reyes", "Harbor master",
        "Fifty-five, weather-cured, a chest full of ribbons. He carries himself like a man who has never "
        "once worried about the law.",
        topics=(
            Topic("stage", "Your evening",
                  "\"I presented the Harbor Award at ten past ten. Victor was supposed to hand it to me himself "
                  "and he never came. I stood on that stage for fifteen minutes.\""),
            Topic("victor", "Your arrangement with Victor",
                  "\"Everyone in this port has an arrangement with someone. Mine was older than the war. "
                  "Victor made it. Victor, God rest him, was not careful about the paperwork.\"",
                  requires=("real_ledger",)),
        ),
        reactions=(
            Reaction("photo_1015", "\"There I am. Fifteen minutes in front of three hundred witnesses. "
                                   "Arrest me for the plaque if you like.\""),
            Reaction("reyes_car",
                     "He sighs. \"I collected a parcel at Pier 9 at eleven. Blank pages. Victor baited me, the "
                     "old fox. I wanted that book burned, Detective, not its owner dead. A dead Victor with a "
                     "ledger loose is worse for me than a live one.\""),
            Reaction("decoy_ledger", "\"Yes, a decoy. And I fell for it. At least I got to read my own name "
                                     "in his handwriting.\""),
            Reaction("real_ledger", "\"Five hundred a month, yes. Arrest me for bribery. I did not kill "
                                    "Victor Halloran.\""),
        ),
    ),
    Character(
        "dray", "Silas Dray", "Owner, Blue Heron Lounge",
        "Fifty, a pinstripe suit, a ring on every finger. Dray smiles as if the smile were a business "
        "expense.",
        topics=(
            Topic("business", "Your business with Halloran",
                  "\"Whiskey, nylons, a little paper. I don't ask what comes off the boats and he didn't ask what "
                  "goes in my cellar. He owed me nothing. His boy owed me four thousand.\""),
        ),
        reactions=(
            Reaction("dray_late", "\"There. Ten forty-six. In my club till then, ask any bartender. I never "
                                  "went near that hotel before that.\""),
            Reaction("dray_goods", "\"Penicillin, nylons, rye. I am a businessman, not a chemist. If you want "
                                   "hospital poisons, ask the people who work in hospitals.\""),
            Reaction("safe_open", "\"Two grand gone? If the kid brings it to me, I'll let you know. He hasn't.\""),
            Reaction("real_ledger", "\"Twelve hundred a month, wholesale. A man can get sentimental about "
                                    "money. Fine. I did not kill him.\""),
        ),
    ),
    Character(
        "vera", "Vera Lane", "Singer at the Blue Heron",
        "Thirty, smoke in her voice and mascara she has already given up on. She has the look of someone "
        "who learned of the death an hour ago and is not done being angry about it.",
        topics=(
            Topic("victor", "Your relationship with Victor",
                  "\"He was kind. He wanted to take me away from all this: the smoke, the stage. He brought me "
                  "flowers on Tuesdays. I loved him, Detective, and I did not kill him.\""),
            Topic("heron", "Ask for V.",
                  "\"That's me. When Victor wanted a quiet table and no questions, he said ask for V. at the "
                  "bar.\"", requires=("matchbook",)),
            Topic("upstairs", "Did you see anyone upstairs?",
                  "\"As I left, ten past ten, Dr. Voss was waiting at the end of the corridor, bag in hand. "
                  "She smiled and said she'd look in on him. Funny. He'd said nothing about a doctor "
                  "coming.\"", requires=("two_drops",), gives=("vera_saw",)),
        ),
        reactions=(
            Reaction("lipstick_glass",
                     "She exhales. \"Mine. I went up at ten. He was in a mood. He said, 'Tonight I make two "
                     "drops, Vera. One for the rats and one for the law.' He wouldn't say more. He asked me to "
                     "go at ten past.\"", gives=("two_drops",)),
            Reaction("matchbook", "\"That's how he got me to his side of town. Sweet man.\""),
        ),
    ),
    Character(
        "finch", "Tobias Finch", "Halloran's secretary",
        "Thirty-five, glasses, a briefcase he is holding like a flotation device. Finch has been sweating "
        "through his collar for an hour.",
        topics=(
            Topic("tonight", "Where were you tonight?",
                  "\"At my desk. The manifests. All evening.\" He pushes his glasses up with a shaking finger."),
            Topic("last_hour", "Victor's last hour",
                  "\"I looked in on him at twenty past ten about the manifests. He took a long pull from his "
                  "flask, made a face and said, 'Marcus's brandy is turning.' I left at 10:27.\"",
                  requires=("flask",), gives=("bitter_taste",)),
            Topic("stairs", "What did you see on the back stairs?",
                  "\"At 10:16 I was coming up and Dr. Voss almost knocked me flat going down, her black bag "
                  "clinking. 'He's resting,' she said. 'Don't disturb him.' I did not think of it again "
                  "until now.\"", requires=("finch_courier",), gives=("service_stairs",)),
        ),
        reactions=(
            Reaction("coat_ticket",
                     "He sags onto the nearest crate. \"All right. Victor gave me two parcels. The real ledger "
                     "to Nell's counter for the Inspector, the decoy to Pier 9 for whoever was watching. 'Two "
                     "drops, Tobias,' he said, 'and nobody knows which is real.' I did both. Then I ran.\"",
                     gives=("finch_courier",)),
            Reaction("bitter_taste", "\"It was bitter, yes. I did not think. I thought it was just the brandy.\""),
        ),
    ),
)

HINTS = (
    Hint("lab_report", "Inspector Calloway has the coroner's preliminary report. Ask her about it."),
    Hint("flask", "A man who dies alone in a locked room usually took it in. Search the study."),
    Hint("matchbook", "Go through Victor's pockets of the study: the ashtray might tell you where else he went."),
    Hint("ice_run", "Someone looked after Victor's brandy. Talk to the man who poured it. (Find the flask first.)"),
    Hint("two_drops", "Victor spoke of 'two drops'. The Blue Heron's singer was the last person he confided "
                      "in. Something from the study might loosen her tongue."),
    Hint("coat_ticket", "Two drops, two handovers. Someone ran Victor's errands tonight, and someone at the "
                        "hotel keeps parcels. Ask at the coat check about the Inspector."),
    Hint("real_ledger", "Calloway must authorize the parcel before Nell will release it. Show her what Nell told you."),
    Hint("voss_claim", "Everyone who examined Victor tonight has a story. Dr. Voss's story is the one to pin down."),
    Hint("vera_saw", "Vera left the study at ten past ten. Ask her who else was upstairs."),
    Hint("service_stairs", "Finch lied about his evening, and he has seen someone on the back stairs. Show him "
                           "the coat-check parcel."),
    Hint("ampule_log", "Dr. V. in the ledger. Calloway can get you into the clinic."),
    Hint("deposit_slips", "There is still a desk to search at the clinic."),
)

WRONG = {
    "eleanor": "Calloway reads your notes and shakes her head. \"Eleanor burned a divorce petition and told a lie "
               "about a seating chart. That is a bad marriage, not a murder. And foxglove isn't what killed him.\"",
    "julian": "\"Julian robbed a dying man and he will carry that forever. But he had no way to get injectable "
              "digoxin, and he was nowhere near the flask before ten-thirty.\"",
    "webb": "\"Marcus filled the flask and fetched the ice. Thirty years of loyalty and a hundred polished shoes. "
            "He told you every time you asked. He did not do this.\"",
    "dray": "\"The doorman's log has Dray walking in at 10:46. The poison was already in the flask by then. "
            "And what is in his stock book can't kill that way.\"",
    "vera": "\"Vera sat on that sofa for ten minutes and cried. Lipstick on a glass is not poison.\"",
    "finch": "\"Finch is a coward and a courier. Victor gave him two parcels and he ran both. "
             "He wasn't there when the poison went in.\"",
    "reyes": "\"Reyes was on a stage in front of three hundred people at 10:15, and he wanted the ledger burned, "
             "not its owner dead. Corrupt, yes. Not this.\"",
}

CASE = Case(
    id="double_drop",
    title="The Double Drop",
    tagline="Port Meridian, November 1947",
    briefing=(
        "Rain on the harbor, rain on the glass.\n\n"
        "At midnight, shipping magnate Victor Halloran was found dead in his locked study on the third floor of "
        "the Meridian Grand Hotel, an hour into his own Harbor Gala. A heart attack, says the hotel.\n\n"
        "Inspector Ruth Calloway doesn't buy it, and she can't touch this case officially. Halloran hired you "
        "three days ago. \"If anything happens to me,\" he said, \"look for the two drops.\" He never explained.\n\n"
        "Eight people under that roof had a reason to want him quiet. Find out who killed him, how, and why. "
        "Then say it to Calloway's face, and be sure."
    ),
    locations=LOCATIONS,
    characters=CHARACTERS,
    clues=CLUES,
    suspects=("eleanor", "julian", "webb", "voss", "dray", "vera", "finch", "reyes"),
    culprit="voss",
    hows=(
        Choice("Strangled, then staged as a heart attack"),
        Choice("Injectable digoxin slipped into his flask while his valet was away", correct=True),
        Choice("Foxglove tea from the winter garden"),
        Choice("His own heart pills, crushed into the decanter"),
    ),
    whys=(
        Choice("His will: he was cutting someone out"),
        Choice("To silence him before Monday, when he meant to hand the ledger to the Inspector", correct=True),
        Choice("Jealousy: he was leaving someone for another woman"),
        Choice("To take over his smuggling routes"),
    ),
    hints=HINTS,
    wrong_culprit=WRONG,
    partial_text=(
        "Calloway nods slowly. \"The right name. But how, and why? You gave me a guess. "
        "The DA will want proof of both before he even looks at her. Go back and be sure.\""
    ),
    solved_text=(
        "⚖️ <b>CASE CLOSED</b>\n\n"
        "Dr. Lenora Voss doesn't confess. She only asks to sit down. Then Calloway lays it out, piece by piece: "
        "the ampule shard from St. Anselm's, two missing from her cabinet; four minutes alone with a flask; an empty "
        "chair in a photograph; a doctor running down the back stairs; three hundred dollars a month for six "
        "dock workers who were never allowed to be anything but accidents. She stops asking for anything.\n\n"
        "<b>The double drop.</b> Victor knew he was a dead man the moment he decided to talk. So he made two "
        "handovers in one night. The decoy, blank but for a page of bait, went to Pier 9 for the harbor master and "
        "the loan shark to fight over. The real ledger went across the lobby into a coat-check parcel, into the "
        "only pair of hands in Port Meridian that couldn't be bought. Voss poisoned him to keep the book from the "
        "Inspector. She never knew it had already crossed the lobby.\n\n"
        "<b>Afterwards</b>\n"
        "• Reyes and Dray are arrested within the week. Dray's lawyer is better. Reyes's isn't.\n"
        "• Julian pays his debt, sells the Packard, and starts sleeping again.\n"
        "• Eleanor keeps the winter garden, and the foxglove.\n"
        "• Webb retires. He still polishes the shoes.\n"
        "• Vera sings at the Blue Heron on Tuesdays. She keeps the matchbook.\n"
        "• Finch takes a job in another city. Nell gets a raise from Calloway, off the books.\n"
        "• Calloway lights the cigarette at last."
    ),
    always_met=("calloway",),
    solved_drops=30,
)
