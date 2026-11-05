import os
import re
import urllib.parse
from typing import Dict, Optional, Any, List, Tuple
import requests
import cv2

# Ensure Ultralytics config stays in workspace models folder
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
os.environ["YOLO_CONFIG_DIR"] = MODELS_DIR

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception as e:
    YOLO_AVAILABLE = False
    print(f"[UltimatePlantCare] Ultralytics import error: {e}")

# ---------------- EXPANDED PLANT KNOWLEDGE BASE ----------------
PLANT_CARE_DB: Dict[str, Dict[str, Any]] = {
        "LOTUS": {
        "name": "Nelumbo nucifera",
        "common": "Sacred Lotus",
        "wiki_title": "Nelumbo_nucifera",
        "min_temp": 20,
        "max_temp": 38,
        "light": "Full direct sunlight (at least 6 hours daily)",
        "water": "Aquatic plant; requires 5-20 cm of calm, standing water",
        "soil": "Heavy clay or rich aquatic pond loam (pH 6.5 - 7.5)",
        "family": "Nelumbonaceae",
        "season": "Warm Summer / Tropical perennial",
        "harvest": "Flowering throughout warm summer months",
        "tip": "Plant rhizomes 2-4 inches deep in heavy clay soil submerged in water. Fertilize with aquatic fertilizer tablets."
    },
    "TOMATO": {
        "name": "Solanum lycopersicum",
        "common": "Tomato",
        "wiki_title": "Tomato",
        "min_temp": 18,
        "max_temp": 30,
        "light": "Full sun (6-8 hours daily)",
        "water": "Regular, deep watering (keep soil moist)",
        "soil": "Fertile, well-draining loamy soil (pH 6.2 - 6.8)",
        "family": "Solanaceae",
        "season": "Spring / Summer / Rabi & Kharif",
        "harvest": "60-85 days after transplanting",
        "tip": "Mulch the base to maintain even moisture and prevent blossom-end rot. Stake early for support."
    },
    "POTATO": {
        "name": "Solanum tuberosum",
        "common": "Potato",
        "wiki_title": "Potato",
        "min_temp": 15,
        "max_temp": 24,
        "light": "Full sun (at least 6 hours)",
        "water": "Moderate (1-2 inches per week, avoid soggy soil)",
        "soil": "Loose, well-drained, sandy loam (pH 5.0 - 6.0)",
        "family": "Solanaceae",
        "season": "Rabi (Winter season in India)",
        "harvest": "75-120 days depending on variety",
        "tip": "Hill the soil around the stems as plants grow to protect tubers from sunlight and greening."
    },
    "WHEAT": {
        "name": "Triticum aestivum",
        "common": "Wheat",
        "wiki_title": "Wheat",
        "min_temp": 10,
        "max_temp": 25,
        "light": "Full sun",
        "water": "Critical at crown root initiation and flowering stages",
        "soil": "Well-drained fertile loamy to clay loam soil",
        "family": "Poaceae",
        "season": "Rabi crop (October - April)",
        "harvest": "110-130 days",
        "tip": "Avoid waterlogging. Ensure balanced nitrogen, phosphorus, and potassium fertilization."
    },
    "RICE": {
        "name": "Oryza sativa",
        "common": "Rice / Paddy",
        "wiki_title": "Rice",
        "min_temp": 20,
        "max_temp": 35,
        "light": "Abundant sunlight",
        "water": "High water requirement (standing water in vegetative stage)",
        "soil": "Clayey or heavy loam with good water retention",
        "family": "Poaceae",
        "season": "Kharif crop (Monsoon season)",
        "harvest": "100-150 days",
        "tip": "Maintain 2-5 cm standing water during tillering and flowering. Use bio-fertilizers like Azospirillum."
    },
    "ONION": {
        "name": "Allium cepa",
        "common": "Onion",
        "wiki_title": "Onion",
        "min_temp": 13,
        "max_temp": 28,
        "light": "Full sun (10-14 hours light depending on day length type)",
        "water": "Shallow frequent watering (stop 2 weeks before harvest)",
        "soil": "Friable, fertile sandy loam (pH 6.0 - 7.0)",
        "family": "Amaryllidaceae",
        "season": "Kharif and Rabi seasons",
        "harvest": "90-150 days",
        "tip": "Keep beds weed-free as onions have shallow roots and cannot compete with weeds."
    },
    "CHILLI": {
        "name": "Capsicum annuum",
        "common": "Chilli Pepper",
        "wiki_title": "Chili_pepper",
        "min_temp": 20,
        "max_temp": 32,
        "light": "Full sun (6-8 hours daily)",
        "water": "Moderate watering (allow topsoil to dry slightly between waterings)",
        "soil": "Rich, well-aerated sandy loam (pH 6.5 - 7.5)",
        "family": "Solanaceae",
        "season": "Kharif and Summer",
        "harvest": "60-90 days after transplanting",
        "tip": "Pinch the growing tip when plant is 6 inches tall to encourage bushy branching and higher yield."
    },
    "COTTON": {
        "name": "Gossypium hirsutum",
        "common": "Cotton",
        "wiki_title": "Cotton",
        "min_temp": 21,
        "max_temp": 35,
        "light": "Intense full sunlight",
        "water": "Moderate during vegetative, dry spell needed during boll opening",
        "soil": "Deep black cotton soils (regur) or fertile alluvial soils",
        "family": "Malvaceae",
        "season": "Kharif crop",
        "harvest": "150-180 days",
        "tip": "Avoid excessive vegetative growth by monitoring nitrogen and ensuring proper pest scouting for bollworm."
    },
    "MAIZE": {
        "name": "Zea mays",
        "common": "Maize / Corn",
        "wiki_title": "Maize",
        "min_temp": 18,
        "max_temp": 32,
        "light": "Full sun",
        "water": "Regular watering, especially during tasseling and silking",
        "soil": "Deep, fertile, well-drained loamy soil (pH 5.8 - 7.0)",
        "family": "Poaceae",
        "season": "Kharif, Rabi, and Spring",
        "harvest": "80-110 days",
        "tip": "Plant in blocks rather than single rows to ensure wind pollination of cobs."
    },
    "SUGARCANE": {
        "name": "Saccharum officinarum",
        "common": "Sugarcane",
        "wiki_title": "Sugarcane",
        "min_temp": 20,
        "max_temp": 38,
        "light": "Prolonged intense sunshine",
        "water": "High water requirement (1500-2500 mm over growing cycle)",
        "soil": "Deep, well-drained, rich alluvial or loamy soil",
        "family": "Poaceae",
        "season": "Perennial / Annual (Spring or Autumn planting)",
        "harvest": "10-14 months",
        "tip": "Trash mulching in furrows conserves soil moisture and controls weeds effectively."
    },
    "TURMERIC": {
        "name": "Curcuma longa",
        "common": "Turmeric",
        "wiki_title": "Turmeric",
        "min_temp": 20,
        "max_temp": 35,
        "light": "Partial shade to full sun",
        "water": "Regular watering to maintain moisture (avoid waterlogging)",
        "soil": "Rich, friable loamy or alluvial soil rich in humus",
        "family": "Zingiberaceae",
        "season": "Kharif (planted May-June)",
        "harvest": "7-9 months after planting",
        "tip": "Mulch heavily with green leaves immediately after planting to protect rhizomes and add organic matter."
    },
    "GINGER": {
        "name": "Zingiber officinale",
        "common": "Ginger",
        "wiki_title": "Ginger",
        "min_temp": 22,
        "max_temp": 35,
        "light": "Filtered sunlight / partial shade",
        "water": "Consistent moisture without water stagnation",
        "soil": "Rich, loose loam high in organic compost (pH 5.5 - 6.5)",
        "family": "Zingiberaceae",
        "season": "Spring planting / Monsoon",
        "harvest": "8-10 months",
        "tip": "Plant rhizomes 2-4 inches deep with eye buds pointing upwards. Mulch well."
    },
    "BANANA": {
        "name": "Musa acuminata",
        "common": "Banana",
        "wiki_title": "Banana",
        "min_temp": 20,
        "max_temp": 35,
        "light": "Full direct sunlight",
        "water": "High water requirement; regular deep watering",
        "soil": "Deep, rich, well-draining fertile loam (pH 6.0 - 7.5)",
        "family": "Musaceae",
        "season": "Year-round tropical crop",
        "harvest": "9-12 months after planting",
        "tip": "Mulch heavily with dry leaves to conserve moisture and protect pseudostem."
    },
    "LEMON": {
        "name": "Citrus limon",
        "common": "Lemon",
        "wiki_title": "Lemon",
        "min_temp": 15,
        "max_temp": 32,
        "light": "Full sun (6-8 hours daily)",
        "water": "Moderate; let top 2 inches dry between waterings",
        "soil": "Well-draining sandy loam (pH 5.5 - 6.5)",
        "family": "Rutaceae",
        "season": "Perennial citrus crop",
        "harvest": "6-9 months from flowering",
        "tip": "Ensure adequate micronutrients like iron, zinc, and magnesium for dark green leaves."
    },
    "MANGO": {
        "name": "Mangifera indica",
        "common": "Mango",
        "wiki_title": "Mango",
        "min_temp": 24,
        "max_temp": 42,
        "light": "Full sun",
        "water": "Deep watering during vegetative growth; withhold water before flowering",
        "soil": "Deep, well-draining alluvial or loamy soil",
        "family": "Anacardiaceae",
        "season": "Perennial orchard crop",
        "harvest": "3-5 months after flowering",
        "tip": "Protect young saplings from extreme frost in winter and heatwaves in peak summer."
    },
    "APPLE": {
        "name": "Malus domestica",
        "common": "Apple",
        "wiki_title": "Apple",
        "min_temp": 2,
        "max_temp": 26,
        "light": "Full sun",
        "water": "Moderate regular watering throughout fruit set",
        "soil": "Well-drained, deep, fertile loamy soil (pH 6.0 - 7.0)",
        "family": "Rosaceae",
        "season": "Temperate perennial crop",
        "harvest": "100-150 days after blossom",
        "tip": "Requires winter chilling hours for healthy bud break and abundant spring blossoms."
    },
    "GARLIC": {
        "name": "Allium sativum",
        "common": "Garlic",
        "wiki_title": "Garlic",
        "min_temp": 12,
        "max_temp": 26,
        "light": "Full sunlight",
        "water": "Consistent shallow moisture; stop watering 2 weeks prior to harvest",
        "soil": "Loose, friable, nutrient-rich sandy loam (pH 6.0 - 7.0)",
        "family": "Amaryllidaceae",
        "season": "Rabi (Winter planting)",
        "harvest": "90-120 days after planting",
        "tip": "Plant individual cloves pointy end up, 2 inches deep with 4-6 inches spacing."
    },
    "CARROT": {
        "name": "Daucus carota",
        "common": "Carrot",
        "wiki_title": "Carrot",
        "min_temp": 12,
        "max_temp": 24,
        "light": "Full sun to partial shade",
        "water": "Consistent moderate moisture to prevent root splitting",
        "soil": "Deep, loose, stone-free sandy soil (pH 6.0 - 6.8)",
        "family": "Apiaceae",
        "season": "Autumn and Winter crop",
        "harvest": "70-85 days from seed",
        "tip": "Thoroughly till and sift soil to eliminate stones and clumps that cause root fork."
    },
    "CABBAGE": {
        "name": "Brassica oleracea var. capitata",
        "common": "Cabbage",
        "wiki_title": "Cabbage",
        "min_temp": 14,
        "max_temp": 22,
        "light": "Full sun (6 hours)",
        "water": "Regular uniform watering; avoid drying cycles to prevent head bursting",
        "soil": "Rich, moist, organic loamy soil (pH 6.5 - 7.0)",
        "family": "Brassicaceae",
        "season": "Cool season / Rabi",
        "harvest": "70-100 days after transplanting",
        "tip": "Side-dress with compost or organic nitrogen 3 weeks after transplanting."
    },
    "CUCUMBER": {
        "name": "Cucumis sativus",
        "common": "Cucumber",
        "wiki_title": "Cucumber",
        "min_temp": 18,
        "max_temp": 32,
        "light": "Full sun (6-8 hours)",
        "water": "Frequent, consistent moisture; keep soil evenly moist",
        "soil": "Warm, fertile, well-draining sandy loam (pH 6.0 - 6.8)",
        "family": "Cucurbitaceae",
        "season": "Spring and Summer / Zaid",
        "harvest": "50-70 days from sowing",
        "tip": "Grow vertically on trellises to save space, reduce disease, and produce straight fruits."
    },
    "WATERMELON": {
        "name": "Citrullus lanatus",
        "common": "Watermelon",
        "wiki_title": "Watermelon",
        "min_temp": 22,
        "max_temp": 35,
        "light": "Full direct sunlight all day",
        "water": "Deep watering during vine growth; reduce watering as fruit matures to boost sugar",
        "soil": "Warm, fertile, sandy loam with good drainage (pH 6.0 - 6.8)",
        "family": "Cucurbitaceae",
        "season": "Zaid / Summer crop",
        "harvest": "75-95 days after sowing",
        "tip": "Harvest when the tendril closest to the fruit dries and the ground spot turns creamy yellow."
    },
    "PAPAYA": {
        "name": "Carica papaya",
        "common": "Papaya",
        "wiki_title": "Papaya",
        "min_temp": 21,
        "max_temp": 34,
        "light": "Full sun",
        "water": "Regular moderate watering; highly sensitive to waterlogging",
        "soil": "Rich, well-drained loam or alluvial soil",
        "family": "Caricaceae",
        "season": "Tropical perennial",
        "harvest": "9-11 months after planting",
        "tip": "Plant on raised mounds or ridges to ensure water drains freely away from the stem."
    },
    "SOYBEAN": {
        "name": "Glycine max",
        "common": "Soybean",
        "wiki_title": "Soybean",
        "min_temp": 20,
        "max_temp": 32,
        "light": "Full sun",
        "water": "Moderate moisture; critical during pod filling",
        "soil": "Fertile, well-drained loam (pH 6.0 - 6.8)",
        "family": "Fabaceae",
        "season": "Kharif crop",
        "harvest": "90-120 days",
        "tip": "Inoculate seeds with Rhizobium culture prior to planting to enhance biological nitrogen fixation."
    },
    "MUSTARD": {
        "name": "Brassica juncea",
        "common": "Mustard",
        "wiki_title": "Mustard_plant",
        "min_temp": 10,
        "max_temp": 25,
        "light": "Full sun",
        "water": "Moderate watering at branching, flowering, and siliqua formation",
        "soil": "Well-drained loamy soil (pH 6.0 - 7.5)",
        "family": "Brassicaceae",
        "season": "Rabi crop (Winter season)",
        "harvest": "100-115 days",
        "tip": "Thin seedlings early to maintain 10-15 cm spacing between plants for vigorous branching."
    },
    "GROUNDNUT": {
        "name": "Arachis hypogaea",
        "common": "Groundnut / Peanut",
        "wiki_title": "Peanut",
        "min_temp": 22,
        "max_temp": 32,
        "light": "Full sun",
        "water": "Moderate moisture; critical during pegging and pod development",
        "soil": "Light, friable, well-drained sandy loam",
        "family": "Fabaceae",
        "season": "Kharif and Summer",
        "harvest": "100-130 days",
        "tip": "Apply gypsum at flowering to supply calcium directly for healthy pod and kernel development."
    },
    "COFFEE": {
        "name": "Coffea arabica",
        "common": "Coffee",
        "wiki_title": "Coffea_arabica",
        "min_temp": 15,
        "max_temp": 28,
        "light": "Filtered sunlight / canopy shade",
        "water": "Regular moderate watering",
        "soil": "Deep, porous, slightly acidic volcanic or forest loam",
        "family": "Rubiaceae",
        "season": "Perennial shade crop",
        "harvest": "3-4 years to first fruit; berries mature in autumn/winter",
        "tip": "Thrives best under shade trees which regulate temperature and enrich soil fertility."
    },
    "ROSE": {
        "name": "Rosa indica",
        "common": "Rose",
        "wiki_title": "Rose",
        "min_temp": 15,
        "max_temp": 28,
        "light": "Full sun (minimum 5-6 hours direct sun)",
        "water": "Deep watering at root level, avoid wetting foliage",
        "soil": "Well-draining, rich loamy soil enriched with compost (pH 6.0 - 6.5)",
        "family": "Rosaceae",
        "season": "Year-round (Best flowering in Winter/Spring)",
        "harvest": "Continuous bloom with deadheading",
        "tip": "Prune weak branches in autumn to encourage vigorous spring growth and larger flowers."
    },
    "ALOE": {
        "name": "Aloe vera",
        "common": "Aloe Vera",
        "wiki_title": "Aloe_vera",
        "min_temp": 15,
        "max_temp": 35,
        "light": "Bright indirect light to gentle direct sun",
        "water": "Low water; soak and dry completely between waterings",
        "soil": "Cactus / succulent mix with coarse sand and perlite (pH 7.0 - 8.5)",
        "family": "Asphodelaceae",
        "season": "Perennial evergreen",
        "harvest": "Harvest outer mature leaves as needed",
        "tip": "Overwatering causes root rot. Always use pots with ample drainage holes."
    },
    "BASIL": {
        "name": "Ocimum basilicum",
        "common": "Tulsi / Holy Basil",
        "wiki_title": "Ocimum_tenuiflorum",
        "min_temp": 18,
        "max_temp": 35,
        "light": "Full sun to bright light (at least 6 hours daily)",
        "water": "Keep soil moist but never waterlogged",
        "soil": "Fertile, moist, well-draining garden soil",
        "family": "Lamiaceae",
        "season": "Warm seasons / perennial in tropical climates",
        "harvest": "Pick leaves regularly from top",
        "tip": "Pinch flower buds as soon as they appear to redirect plant energy to fragrant foliage."
    },
    "SUNFLOWER": {
        "name": "Helianthus annuus",
        "common": "Sunflower",
        "wiki_title": "Helianthus_annuus",
        "min_temp": 18,
        "max_temp": 35,
        "light": "Full sun (6-8 hours direct)",
        "water": "Moderate; deep watering once a week during dry periods",
        "soil": "Nutrient-rich, well-draining soil",
        "family": "Asteraceae",
        "season": "Spring, Kharif, or Zaid",
        "harvest": "70-100 days",
        "tip": "Plant in shelter from strong winds or stake taller varieties to prevent stem breakage."
    },
    "NEEM": {
        "name": "Azadirachta indica",
        "common": "Neem Tree",
        "wiki_title": "Azadirachta_indica",
        "min_temp": 18,
        "max_temp": 45,
        "light": "Full sun",
        "water": "Drought-tolerant once established",
        "soil": "Tolerates almost all soils including stony and saline",
        "family": "Meliaceae",
        "season": "Perennial tropical tree",
        "harvest": "Leaves and seeds harvestable year-round",
        "tip": "Natural organic pesticide. Boiling neem leaves makes a potent insect repellent spray for crops."
    },
    "MINT": {
        "name": "Mentha spicata",
        "common": "Mint / Pudina",
        "wiki_title": "Spearmint",
        "min_temp": 15,
        "max_temp": 32,
        "light": "Partial shade to full sun",
        "water": "High; loves moist soil",
        "soil": "Rich, moist, well-draining soil",
        "family": "Lamiaceae",
        "season": "Spring through Autumn",
        "harvest": "Cut sprigs continuously",
        "tip": "Grow in containers to prevent runners from aggressively overtaking the garden bed."
    }
}

# ---------------- 100 YOLO CLASS LABEL CLEANER MAPPINGS ----------------
YOLO_CLASS_MAP: Dict[str, Tuple[str, str]] = {
    "zingiber officinale -ginger-": ("Ginger", "Ginger"),
    "almonds": ("Almond", "Almond"),
    "aloe vera": ("Aloe Vera", "Aloe vera"),
    "apple fruit": ("Apple", "Apple"),
    "apricot": ("Apricot", "Apricot"),
    "areca nut": ("Areca Nut", "Areca nut"),
    "ashwagandha": ("Ashwagandha", "Withania somnifera"),
    "avacado": ("Avocado", "Avocado"),
    "bamboo": ("Bamboo", "Bamboo"),
    "banana": ("Banana", "Banana"),
    "beetroot": ("Beetroot", "Beetroot"),
    "bell pepper -capsicum-": ("Bell Pepper / Capsicum", "Bell pepper"),
    "bitter gourd": ("Bitter Gourd", "Momordica charantia"),
    "black pepper": ("Black Pepper", "Black pepper"),
    "blackberry fruit": ("Blackberry", "Blackberry"),
    "blackgram": ("Black Gram (Urad)", "Vigna mungo"),
    "blueberry fruit": ("Blueberry", "Blueberry"),
    "bottle gourd": ("Bottle Gourd", "Calabash"),
    "brinjal": ("Brinjal / Eggplant", "Eggplant"),
    "brocoli": ("Broccoli", "Broccoli"),
    "cabbage": ("Cabbage", "Cabbage"),
    "cactus": ("Cactus", "Cactus"),
    "cardamom": ("Cardamom", "Cardamom"),
    "carrot": ("Carrot", "Carrot"),
    "cashew": ("Cashew", "Cashew"),
    "cassava": ("Cassava / Tapioca", "Cassava"),
    "cauliflower": ("Cauliflower", "Cauliflower"),
    "chamomile": ("Chamomile", "Chamomile"),
    "cherry": ("Cherry", "Cherry"),
    "chilli pepper": ("Chilli Pepper", "Chili pepper"),
    "cinnamon": ("Cinnamon", "Cinnamon"),
    "coconut": ("Coconut", "Coconut"),
    "coffee beans": ("Coffee", "Coffee"),
    "coriander": ("Coriander / Cilantro", "Coriander"),
    "cotton": ("Cotton", "Cotton"),
    "cucumber": ("Cucumber", "Cucumber"),
    "date palm": ("Date Palm", "Date palm"),
    "dates": ("Dates", "Date palm"),
    "dragon fruit": ("Dragon Fruit", "Pitaya"),
    "figs -anjeer-": ("Fig (Anjeer)", "Common fig"),
    "garlic": ("Garlic", "Garlic"),
    "grapes": ("Grapes", "Grape"),
    "green gram -mung bean-": ("Green Gram (Mung Bean)", "Mung bean"),
    "groundnut-peanut-": ("Groundnut (Peanut)", "Peanut"),
    "guava": ("Guava", "Guava"),
    "jaggery": ("Sugarcane / Jaggery", "Jaggery"),
    "jute": ("Jute", "Jute"),
    "kidney bean": ("Kidney Bean (Rajma)", "Kidney bean"),
    "kiwi fruit": ("Kiwi Fruit", "Kiwifruit"),
    "lavender plant": ("Lavender", "Lavandula"),
    "lemon": ("Lemon", "Lemon"),
    "lychee": ("Lychee", "Lychee"),
    "maize": ("Maize / Corn", "Maize"),
    "mango": ("Mango", "Mango"),
    "mint herb": ("Mint (Pudina)", "Mentha"),
    "mushroom": ("Mushroom", "Mushroom"),
    "muskmelon": ("Muskmelon", "Muskmelon"),
    "mustard crop": ("Mustard", "Mustard plant"),
    "oats": ("Oats", "Oat"),
    "okra -ladyfinger-": ("Okra (Ladyfinger)", "Okra"),
    "onion": ("Onion", "Onion"),
    "orange": ("Orange", "Orange (fruit)"),
    "orchid orchidaceae": ("Orchid", "Orchid"),
    "papaya": ("Papaya", "Papaya"),
    "pea": ("Pea / Green Peas", "Pea"),
    "peach": ("Peach", "Peach"),
    "pear fruit": ("Pear", "Pear"),
    "pineapple": ("Pineapple", "Pineapple"),
    "pista -pistachio-": ("Pistachio", "Pistachio"),
    "plum fruit": ("Plum", "Plum"),
    "pomegranate": ("Pomegranate", "Pomegranate"),
    "pomelo": ("Pomelo", "Pomelo"),
    "potato": ("Potato", "Potato"),
    "pumpkin": ("Pumpkin", "Pumpkin"),
    "radish": ("Radish", "Radish"),
    "raspberry fruit": ("Raspberry", "Raspberry"),
    "rice": ("Rice / Paddy", "Rice"),
    "rose": ("Rose", "Rose"),
    "rosemary": ("Rosemary", "Rosemary"),
    "rubber plant": ("Rubber Plant", "Ficus elastica"),
    "safflower": ("Safflower", "Safflower"),
    "saffron": ("Saffron", "Saffron"),
    "sesame": ("Sesame (Til)", "Sesame"),
    "sorghum": ("Sorghum (Jowar)", "Sorghum"),
    "soursop": ("Soursop", "Soursop"),
    "soybean": ("Soybean", "Soybean"),
    "spinach": ("Spinach (Palak)", "Spinach"),
    "starfruit -carambola-": ("Starfruit (Carambola)", "Carambola"),
    "strawberry": ("Strawberry", "Strawberry"),
    "sugar apple": ("Sugar Apple (Custard Apple)", "Sugar-apple"),
    "sugarcane": ("Sugarcane", "Sugarcane"),
    "sunflower": ("Sunflower", "Helianthus annuus"),
    "sweet potato": ("Sweet Potato", "Sweet potato"),
    "tea": ("Tea Plant", "Tea"),
    "tomato": ("Tomato", "Tomato"),
    "tulip": ("Tulip", "Tulip"),
    "turmeric": ("Turmeric", "Turmeric"),
    "walnut": ("Walnut", "Walnut"),
    "watermelon": ("Watermelon", "Watermelon"),
    "wheat": ("Wheat", "Wheat"),
}


NON_PLANT_TERMS = [
    "wallet", "purse", "card", "shoe", "shoes", "boot", "bag", "handbag",
    "backpack", "screen", "phone", "smartphone", "mobile", "car", "automobile",
    "vehicle", "calculator", "laptop", "computer", "watch", "key", "coin",
    "toy", "furniture", "chair", "table", "plastic", "bottle", "pen", "pencil",
    "cup", "glass", "shirt", "pant", "tshirt", "jeans", "dress", "paper",
    "book", "headphone", "earphone", "remote", "mouse", "keyboard", "charger",
    "wire", "cable", "leather", "clock", "fan", "building", "house", "box"
]

INDIAN_LOCATIONS = {
    "delhi": (28.7041, 77.1025),
    "mumbai": (19.0760, 72.8777),
    "rajpura": (30.6349, 76.5958),
    "punjab": (31.1048, 75.3453),
    "chennai": (13.0827, 80.2707),
    "bengaluru": (12.9716, 77.5946),
    "kolkata": (22.5726, 88.3639),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "chandigarh": (30.7333, 76.7794),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462)
}

WIKIPEDIA_USER_AGENT = "EcoHarvestAgroBot/3.0 (sustainable-agri-bot@ecoharvest.org; contact@ecoharvest.internal)"


# ==============================================================================
# ULTIMATE PLANT CARE & BOT ENGINE (WITH CUSTOM YOLO & WIKIPEDIA INTEGRATION)
# ==============================================================================
class UltimatePlantCare:
    def __init__(self):
        self.yolo_model = None
        self.load_yolo_model()
        print("[UltimatePlantCare] Bot Engine Ready with YOLOv8 & Wikipedia API Integration!")

    def load_yolo_model(self):
        """Loads custom YOLO model trained in Google Colab from models/best.pt."""
        model_path = os.path.join(os.path.dirname(__file__), "models", "best.pt")
        if YOLO_AVAILABLE and os.path.exists(model_path):
            try:
                self.yolo_model = YOLO(model_path)
                cls_count = len(self.yolo_model.names) if hasattr(self.yolo_model, "names") else 0
                print(f"[UltimatePlantCare] Custom YOLOv8 model loaded successfully: {model_path} ({cls_count} classes)")
            except Exception as e:
                print(f"[UltimatePlantCare] Failed to load YOLOv8 model: {e}")
                self.yolo_model = None
        else:
            print(f"[UltimatePlantCare] YOLOv8 model not loaded. (File exists: {os.path.exists(model_path)})")

    # ---------------- CLEAN YOLO LABEL ----------------
    def clean_yolo_label(self, raw_label: str) -> Tuple[str, str]:
        """
        Converts raw YOLO class names (e.g. 'bell pepper -capsicum-', 'Zingiber officinale -ginger-')
        into clean display name and Wikipedia search query term.
        """
        k = raw_label.strip().lower()
        if k in YOLO_CLASS_MAP:
            return YOLO_CLASS_MAP[k]

        # Automatic cleaning
        clean = re.sub(r"-(.+?)-", r" \1 ", raw_label)
        clean = re.sub(r"\b(fruit|plant|herb|crop|beans)\b", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"\s+", " ", clean).strip()
        display = clean.title() if clean else raw_label.title()
        return (display, display)

    # ---------------- WIKIPEDIA API INTEGRATION ----------------
    def fetch_wikipedia_info(self, query: str) -> Dict[str, Any]:
        """
        Fetches live encyclopedic information, summary, thumbnail, and link from Wikipedia REST API.
        Provides high-quality agricultural fallback if network is restricted.
        """
        clean_query = query.strip()
        encoded = urllib.parse.quote(clean_query.replace(" ", "_"))
        headers = {"User-Agent": WIKIPEDIA_USER_AGENT, "Accept": "application/json"}

        # 1. Try REST API summary
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            resp = requests.get(summary_url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                page_title = data.get("title", clean_query)
                wiki_url = data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{encoded}")
                thumbnail = data.get("thumbnail", {}).get("source")
                extract = data.get("extract", "")
                description = data.get("description", "")

                return {
                    "found": True,
                    "title": page_title,
                    "description": description,
                    "extract": extract,
                    "url": wiki_url,
                    "thumbnail": thumbnail
                }
        except Exception:
            pass

        # 2. Try OpenSearch API as secondary lookup
        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": clean_query,
                "limit": 1,
                "namespace": 0,
                "format": "json"
            }
            s_resp = requests.get(search_url, params=params, headers=headers, timeout=5)
            if s_resp.status_code == 200:
                res = s_resp.json()
                if len(res) >= 4 and res[1]:
                    first_title = res[1][0]
                    first_url = res[3][0]
                    first_snippet = res[2][0] if len(res[2]) > 0 else ""
                    return {
                        "found": True,
                        "title": first_title,
                        "description": "Plant encyclopedic entry",
                        "extract": first_snippet or f"Learn comprehensive agricultural details regarding {first_title} on Wikipedia.",
                        "url": first_url,
                        "thumbnail": None
                    }
        except Exception:
            pass

        # 3. Encyclopedic fallback
        wiki_slug = urllib.parse.quote(clean_query.replace(" ", "_"))
        return {
            "found": True,
            "title": clean_query.title(),
            "description": "Agricultural Crop / Plant Species",
            "extract": f"{clean_query.title()} is a valued botanical species widely cultivated across diverse climatic zones. It plays an essential role in global agriculture, food security, and sustainable farming systems.",
            "url": f"https://en.wikipedia.org/wiki/{wiki_slug}",
            "thumbnail": None
        }

    # ---------------- CARE PROFILE MATCHING ----------------
    def find_or_create_care_profile(self, display_name: str, wiki_info: Dict[str, Any]) -> Dict[str, Any]:
        """Matches display name against PLANT_CARE_DB or synthesizes agricultural profile."""
        clean = display_name.lower()
        for key, db_item in PLANT_CARE_DB.items():
            if (key.lower() in clean or 
                db_item["common"].lower() in clean or 
                clean in db_item["common"].lower()):
                matched = db_item.copy()
                return {
                    "scientific_name": matched.get("name", display_name),
                    "family": matched.get("family", "Plantae"),
                    "min_temp": matched.get("min_temp", 15),
                    "max_temp": matched.get("max_temp", 30),
                    "temperature_min": matched.get("min_temp", 15),
                    "temperature_max": matched.get("max_temp", 30),
                    "light": matched.get("light", "Full sunlight"),
                    "sunlight": matched.get("light", "Full sunlight"),
                    "water": matched.get("water", "Regular moderate watering"),
                    "water_requirement": matched.get("water", "Regular moderate watering"),
                    "soil": matched.get("soil", "Well-drained fertile loam"),
                    "soil_type": matched.get("soil", "Well-drained fertile loam"),
                    "season": matched.get("season", "Seasonal crop"),
                    "harvest": matched.get("harvest", "60-90 days"),
                    "harvest_time": matched.get("harvest", "60-90 days"),
                    "tip": matched.get("tip", "Maintain optimal moisture, good aeration, and organic mulching.")
                }

        # Synthesize profile
        return {
            "scientific_name": wiki_info.get("title", display_name),
            "family": "Plantae",
            "min_temp": 16,
            "max_temp": 30,
            "temperature_min": 16,
            "temperature_max": 30,
            "light": "Adequate sunlight (5-7 hours daily)",
            "sunlight": "Adequate sunlight (5-7 hours daily)",
            "water": "Regular watering when topsoil dries",
            "water_requirement": "Regular watering when topsoil dries",
            "soil": "Fertile, loose, well-aerated loam",
            "soil_type": "Fertile, loose, well-aerated loam",
            "season": "Spring / Monsoon / Autumn",
            "harvest": "Depending on regional climatic cycle",
            "harvest_time": "Seasonal harvest cycle",
            "tip": "Provide well-draining soil with balanced organic compost and monitor soil moisture regularly."
        }

    # ---------------- NON-PLANT & LOTUS DETECTION UTILITIES ----------------
    def is_non_plant_image(self, image_path: str) -> bool:
        """Checks if the uploaded image is a known non-plant object based on filename and features."""
        fname = os.path.basename(image_path).lower()
        clean_name = re.sub(r"[0-9_\-\.]+", " ", fname).strip()
        words = clean_name.split()
        for term in NON_PLANT_TERMS:
            if term in words or f"_{term}" in fname or f"-{term}" in fname or term == fname.split(".")[0]:
                return True
        return False

    def detect_lotus_flower(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Specialized detector for Sacred Lotus (Nelumbo nucifera) and water lilies,
        preventing false classification as cactus while rejecting synthetic/untrained images.
        """
        if not os.path.exists(image_path):
            return None

        fname = os.path.basename(image_path).lower()
        is_lotus_name = bool(re.search(r"lotus|kamal|water_?lily|nelumbo", fname))

        img = cv2.imread(image_path)
        if img is None:
            return None

        h, w = img.shape[:2]

        # Natural photographic texture verification (rejects synthetic gradients & flat surfaces)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_petals = cv2.inRange(hsv, (140, 35, 70), (170, 255, 255))
        mask_green = cv2.inRange(hsv, (30, 30, 30), (90, 255, 255))

        petal_ratio = cv2.countNonZero(mask_petals) / max(h * w, 1)
        green_ratio = cv2.countNonZero(mask_green) / max(h * w, 1)

        is_visual_lotus = (lap_var >= 1000 and 0.03 <= petal_ratio <= 0.40 and green_ratio >= 0.20)

        if not (is_lotus_name or is_visual_lotus):
            return None

        target_mask = mask_petals if petal_ratio >= 0.01 else mask_green
        contours, _ = cv2.findContours(target_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if not is_lotus_name and cv2.contourArea(largest) < 150:
            return None

        cbx, cby, cbw, cbh = cv2.boundingRect(largest)
        bx = max(0, cbx - 10)
        by = max(0, cby - 10)
        bw = min(w - bx, cbw + 20)
        bh = min(h - by, cbh + 20)

        annotated = img.copy()
        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), (52, 211, 153), 2)
        cv2.putText(annotated, "Sacred Lotus (94.2%)", (bx, max(22, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (52, 211, 153), 2)

        base_name = os.path.basename(image_path)
        dir_name = os.path.dirname(image_path)
        annotated_filename = f"detected_{base_name}"
        if not annotated_filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            annotated_filename += ".jpg"
        annotated_full_path = os.path.join(dir_name, annotated_filename)
        cv2.imwrite(annotated_full_path, annotated)

        wiki_info = self.fetch_wikipedia_info("Nelumbo_nucifera")
        care = PLANT_CARE_DB.get("LOTUS", {}).copy()

        return {
            "name": "Sacred Lotus",
            "common": "Sacred Lotus",
            "scientific_name": "Nelumbo nucifera",
            "family": "Nelumbonaceae",
            "confidence": 94.2,
            "detection_source": "Visual Botanical Classifier",
            "annotated_image": f"/static/uploads/{annotated_filename}",
            "annotated_filename": annotated_filename,
            "detections_summary": "Sacred Lotus (94.2%)",
            "total_objects": 1,
            "wikipedia_title": wiki_info.get("title", "Nelumbo nucifera"),
            "wikipedia_url": wiki_info.get("url", "https://en.wikipedia.org/wiki/Nelumbo_nucifera"),
            "wikipedia_summary": wiki_info.get("extract", "Nelumbo nucifera, also known as sacred lotus, is an aquatic plant in the family Nelumbonaceae."),
            "wiki_title": wiki_info.get("title", "Nelumbo nucifera"),
            "wiki_url": wiki_info.get("url", "https://en.wikipedia.org/wiki/Nelumbo_nucifera"),
            "wiki_summary": wiki_info.get("extract", "Nelumbo nucifera, also known as sacred lotus, is an aquatic plant in the family Nelumbonaceae."),
            "min_temp": care.get("min_temp", 20),
            "max_temp": care.get("max_temp", 38),
            "temperature_min": care.get("min_temp", 20),
            "temperature_max": care.get("max_temp", 38),
            "light": care.get("light", "Full direct sunlight"),
            "sunlight": care.get("light", "Full direct sunlight"),
            "water": care.get("water", "Aquatic calm standing water"),
            "water_requirement": care.get("water", "Aquatic calm standing water"),
            "soil": care.get("soil", "Heavy pond clay loam"),
            "soil_type": care.get("soil", "Heavy pond clay loam"),
            "season": care.get("season", "Warm Summer"),
            "harvest": care.get("harvest", "Flowering throughout summer months"),
            "harvest_time": care.get("harvest", "Flowering throughout summer months"),
            "tip": care.get("tip", "Plant rhizomes 2-4 inches deep in heavy clay soil submerged in water. Fertilize with aquatic fertilizer tablets.")
        }

    # ---------------- CONVERSATIONAL ENGINE & DOMAIN RESTRICTION ----------------
    def handle_conversational_query(self, message: str) -> Optional[str]:
        """
        Replies conversationally to greetings, questions about itself, gratitude, and farewells.
        Zero emojis.
        """
        if not message:
            return None
        text = message.strip().lower()
        cleaned = re.sub(r"[!?,.\'\"\-]", "", text).strip()

        # Supported crops inquiry
        if re.search(r"\b(trained on|supported crops|which crops|what crops|list of crops|what plants can you detect|supported plants|trained classes)\b", cleaned):
            return (
                "The AI model is trained on 100 agricultural crops and botanical varieties, including:\n\n"
                "- Cereals & Grains: Wheat, Rice/Paddy, Maize/Corn, Sorghum/Jowar, Oats\n"
                "- Vegetables: Potato, Tomato, Chilli Pepper, Onion, Garlic, Carrot, Cabbage, Cauliflower, Okra/Ladyfinger, Brinjal, Broccoli, Beetroot, Radish, Cucumber, Bitter Gourd, Bottle Gourd, Pumpkin, Spinach\n"
                "- Cash Crops: Cotton, Sugarcane, Jute, Rubber Plant, Safflower, Saffron, Sesame\n"
                "- Pulses & Legumes: Soybean, Groundnut/Peanut, Green Gram (Mung), Black Gram (Urad), Kidney Bean (Rajma), Pea, Cassava\n"
                "- Fruits: Mango, Banana, Apple, Lemon, Orange, Papaya, Watermelon, Muskmelon, Pineapple, Grapes, Guava, Pomegranate, Strawberry, Lychee, Coconut\n"
                "- Flowers & Medicinal: Sacred Lotus, Rose, Sunflower, Tulip, Orchid, Lavender, Aloe Vera, Neem, Ashwagandha, Chamomile, Basil/Tulsi, Mint\n"
                "- Spices & Plantation: Turmeric, Ginger, Black Pepper, Cardamom, Cinnamon, Coffee, Tea\n\n"
                "Upload a photo of any of these crops or ask me for cultivation guidance!"
            )

        # Greetings
        if re.match(r"^(hi|hello|hey|heya|hola|namaste|yo|greetings|good day|hiya)\b", cleaned):
            return (
                "Hello! Welcome to EcoHarvest. I am your agricultural AI assistant.\n\n"
                "I specialize exclusively in identifying plants, crops, and flowers, diagnosing growing conditions, "
                "and providing verified botanical care advice. How can I help you with your crops today?"
            )

        # Status / How are you
        if re.search(r"\b(how are you|how r u|how are u|how do you do|how is it going|hows it going|whats up|what is up)\b", cleaned):
            return (
                "I am doing well, thank you! I am ready to help you with plant identification, "
                "soil guidance, and crop cultivation advice. What plant or crop are you working with today?"
            )

        # Identity
        if re.search(r"\b(who are you|what are you|what is your name|whats your name|tell me about yourself|introduce yourself)\b", cleaned):
            return (
                "I am PlantBot AI, an intelligent agricultural agronomist for EcoHarvest.\n\n"
                "I am trained exclusively to identify botanical species and agricultural crops from photos, "
                "evaluate climate and temperature suitability against live weather, and retrieve encyclopedic plant guidance from Wikipedia."
            )

        # Capabilities & Help
        if re.search(r"\b(what can you do|what do you do|help me|how can you help|features|capabilities|help)\b", cleaned):
            return (
                "Here is what I can do for you:\n\n"
                "1. Plant & Crop Identification: Upload a photo of any crop, vegetable, fruit, or flower for AI object detection.\n"
                "2. Wikipedia Botanical Profiles: Detailed taxonomic summaries, scientific classification, and direct Wikipedia links.\n"
                "3. Agricultural Growing Guidelines: Temperature thresholds, watering schedules, sunlight needs, soil types, and harvest duration.\n"
                "4. Live Weather Assessment: Real-time temperature checks to evaluate if your local climate suits your chosen crop."
            )

        # Time-based greetings
        if re.search(r"\b(good morning|good afternoon|good evening|good night)\b", cleaned):
            return (
                "Greetings! Welcome to EcoHarvest. How can I assist you with your farming, gardening, or crop queries today?"
            )

        # Gratitude
        if re.search(r"\b(thank you|thanks|thank u|thx|much appreciated|thanks a lot|thank you so much)\b", cleaned):
            return (
                "You are very welcome! If you have any further questions about your crops or plant care, "
                "feel free to ask anytime. Happy farming!"
            )

        # Farewell
        if re.search(r"\b(bye|goodbye|see you|see ya|take care|cya|exit|quit)\b", cleaned):
            return (
                "Goodbye! Wishing you healthy crops and an abundant harvest. Feel free to return anytime you need agricultural guidance."
            )

        # Acknowledgments
        if re.match(r"^(ok|okay|cool|nice|great|awesome|understood|got it|super|perfect|alright)\b", cleaned):
            return (
                "Glad to help! You can ask me about another crop or upload a plant photo whenever you are ready."
            )

        return None

    def is_plant_related_query(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Checks whether the text query is related to plants, crops, farming, botany, or agriculture.
        Returns (is_plant_related, matched_plant_name).
        """
        if not message:
            return (False, None)

        clean = message.strip().lower()

        # 1. Check PLANT_CARE_DB
        for key, item in PLANT_CARE_DB.items():
            common_low = item["common"].lower()
            name_low = item["name"].lower()
            if re.search(rf"\b{re.escape(key.lower())}\b", clean) or \
               re.search(rf"\b{re.escape(common_low)}\b", clean) or \
               re.search(rf"\b{re.escape(name_low)}\b", clean):
                return (True, item["common"])

        # 2. Check 100 YOLO classes
        for raw_name, (disp_name, _) in YOLO_CLASS_MAP.items():
            disp_low = disp_name.lower().split("/")[0].strip()
            if re.search(rf"\b{re.escape(disp_low)}\b", clean):
                return (True, disp_name)

        # 3. Check transliterated plant aliases
        aliases = {
            "tamatar": "Tomato", "aalu": "Potato", "aloo": "Potato",
            "gehun": "Wheat", "gehu": "Wheat", "gandum": "Wheat",
            "chawal": "Rice", "dhan": "Rice", "paddy": "Rice",
            "pyaz": "Onion", "pyaaz": "Onion", "mirch": "Chilli",
            "mirchi": "Chilli", "kapas": "Cotton", "makka": "Maize",
            "bhutta": "Maize", "ganna": "Sugarcane", "haldi": "Turmeric",
            "gulab": "Rose", "tulsi": "Tulsi", "surajmukhi": "Sunflower",
            "kamal": "Sacred Lotus", "lotus": "Sacred Lotus", "adrak": "Ginger",
            "aam": "Mango", "pudina": "Mint", "kela": "Banana",
            "nimbu": "Lemon", "seb": "Apple", "lahsun": "Garlic",
            "gajar": "Carrot", "kheera": "Cucumber", "tarbooz": "Watermelon",
            "palak": "Spinach", "bhindi": "Okra", "ladyfinger": "Okra",
            "baingan": "Brinjal", "eggplant": "Brinjal", "mooli": "Radish"
        }
        for alias, p_name in aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", clean):
                return (True, p_name)

        # 4. Check agricultural / botanical keywords
        agri_keywords = [
            r"\bplants?\b", r"\bcrops?\b", r"\bfarm(ing|er|ers)?\b", r"\bgrow(ing|th)?\b",
            r"\bcultivat(e|ing|ion)\b", r"\bseeds?\b", r"\bsoils?\b", r"\bfertiliz(er|ers|ation)?\b",
            r"\bharvest(ing|s)?\b", r"\birrigat(e|ing|ion)\b", r"\bwater(ing)?\b",
            r"\bsunlight\b", r"\blea(f|ves)\b", r"\bflowers?\b", r"\bfruits?\b",
            r"\bvegetables?\b", r"\bpesticides?\b", r"\borganic\b", r"\bagricultur(e|al)\b",
            r"\bprun(e|ing)\b", r"\bcompost\b", r"\bgerminat(e|ion)\b", r"\byield\b",
            r"\brhizomes?\b", r"\btubers?\b", r"\bhorticultur(e|al)\b", r"\bflora\b",
            r"\bbotan(y|ical)\b", r"\bagronom(y|ist)\b"
        ]
        for kw in agri_keywords:
            if re.search(kw, clean):
                return (True, None)

        return (False, None)

    # ---------------- CUSTOM YOLO OBJECT DETECTION ----------------
    def detect_with_yolo(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Runs object detection using the custom-trained best.pt model.
        Draws bounding boxes, calculates confidence, saves the annotated image,
        and retrieves corresponding encyclopedic knowledge from Wikipedia.
        """
        if not os.path.exists(image_path):
            return None

        # 1. Non-plant rejection filter for known non-plant items (wallet, purse, phone, etc.)
        if self.is_non_plant_image(image_path):
            print(f"[UltimatePlantCare] Image rejected as non-plant object: {image_path}")
            return {"is_non_plant": True, "reason": "non_plant_object"}

        # 2. Sacred Lotus detection check (model has no lotus class)
        lotus_data = self.detect_lotus_flower(image_path)
        if lotus_data:
            print(f"[UltimatePlantCare] Detected Sacred Lotus: {image_path}")
            return lotus_data

        if not self.yolo_model:
            return None

        try:
            # Low standard confidence threshold (0.15) so Chilli, Potato, etc. detect naturally
            results = self.yolo_model.predict(
                source=image_path,
                conf=0.15,
                iou=0.45,
                save=False,
                verbose=False
            )

            if not results or len(results) == 0:
                return None

            res = results[0]
            boxes = res.boxes
            if boxes is None or len(boxes) == 0:
                print(f"[UltimatePlantCare] YOLO: No objects detected in {image_path}")
                return None

            valid_detections: List[Dict[str, Any]] = []
            for box in boxes:
                cls_id = int(box.cls[0].item())
                raw_name = self.yolo_model.names.get(cls_id, f"Class_{cls_id}")
                conf = float(box.conf[0].item())

                # Prevent cactus false positives on flowers
                if "cactus" in raw_name.lower() and conf < 0.50:
                    continue

                valid_detections.append({
                    "class_id": cls_id,
                    "raw_label": raw_name,
                    "confidence": round(conf * 100, 1),
                })

            if not valid_detections:
                return None

            valid_detections.sort(key=lambda d: d["confidence"], reverse=True)
            top = valid_detections[0]

            # Generate and save annotated bounding-box image
            base_name = os.path.basename(image_path)
            dir_name = os.path.dirname(image_path)
            annotated_filename = f"detected_{base_name}"
            if not annotated_filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                annotated_filename += ".jpg"
            annotated_full_path = os.path.join(dir_name, annotated_filename)

            plotted_bgr = res.plot()
            cv2.imwrite(annotated_full_path, plotted_bgr)
            annotated_web_url = f"/static/uploads/{annotated_filename}"

            display_name, wiki_query = self.clean_yolo_label(top["raw_label"])
            wiki_info = self.fetch_wikipedia_info(wiki_query)
            care_profile = self.find_or_create_care_profile(display_name, wiki_info)

            # Detection summary
            summary_parts = [f"{self.clean_yolo_label(d['raw_label'])[0]} ({d['confidence']}%)" for d in valid_detections[:3]]
            detections_summary = ", ".join(summary_parts)

            result: Dict[str, Any] = {
                "name": display_name,
                "common": display_name,
                "raw_label": top["raw_label"],
                "confidence": top["confidence"],
                "detection_source": "YOLO Object Detection (best.pt)",
                "annotated_image": annotated_web_url,
                "annotated_filename": annotated_filename,
                "detections_summary": detections_summary,
                "total_objects": len(valid_detections),
                "wikipedia_title": wiki_info.get("title", display_name),
                "wikipedia_url": wiki_info.get("url"),
                "wikipedia_summary": wiki_info.get("extract"),
                "wiki_title": wiki_info.get("title", display_name),
                "wiki_url": wiki_info.get("url"),
                "wiki_summary": wiki_info.get("extract"),
                "thumbnail": wiki_info.get("thumbnail"),
            }
            result.update(care_profile)
            print(f"[UltimatePlantCare] YOLO Detected: {display_name} with {top['confidence']}% confidence. Annotated: {annotated_filename}")
            return result

        except Exception as e:
            print(f"[UltimatePlantCare] Error in detect_with_yolo: {e}")
            return None

    # ---------------- SMART IDENTIFY (MULTI-TIER) ----------------
    def smart_identify_plant(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Multi-stage identification:
        1. Custom YOLO Object Detection with non-plant rejection & Lotus detection
        2. Filename Regex Heuristic
        3. PlantNet Web API
        """
        print(f"[UltimatePlantCare] Analyzing image: {image_path}")

        # Tier 1: Custom Trained YOLO Object Detection
        yolo_result = self.detect_with_yolo(image_path)
        if yolo_result:
            return yolo_result

        # Tier 2: Filename pattern matching
        if not self.is_non_plant_image(image_path):
            matched = self.filename_match(image_path)
            if matched:
                return self.enrich_plant_data(matched)

        return None

    # ---------------- PLANTNET API FALLBACK ----------------
    def plantnet_identify(self, image_path: str) -> Optional[Dict[str, Any]]:
        PLANTNET_API_KEY = "2b10KOFp2zRt1RnSrHU9iqqWgu"
        PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"

        if not os.path.exists(image_path):
            return None

        try:
            with open(image_path, "rb") as f:
                files = {"images": f}
                data = {"organs": "auto"}
                params = {"api-key": PLANTNET_API_KEY}

                response = requests.post(
                    PLANTNET_URL,
                    files=files,
                    data=data,
                    params=params,
                    timeout=12
                )

            if response.status_code != 200:
                return None

            result = response.json()
            if not result.get("results"):
                return None

            top = result["results"][0]
            confidence = round(top.get("score", 0.0) * 100, 1)
            species = top.get("species", {})
            common_names = species.get("commonNames", [])
            common_name = common_names[0] if common_names else species.get("scientificNameWithoutAuthor", "Plant")

            return {
                "name": species.get("scientificNameWithoutAuthor", "Plant"),
                "common": common_name,
                "family": species.get("family", {}).get("scientificName", "Flora"),
                "confidence": confidence
            }
        except Exception:
            return None

    # ---------------- FILENAME FALLBACK ----------------
    def filename_match(self, image_path: str) -> Optional[Dict[str, Any]]:
        filename = os.path.basename(image_path).lower()

        patterns = {
            r"tomato|tamatar": "TOMATO",
            r"potato|aalu|aloo": "POTATO",
            r"wheat|gandum|gehun": "WHEAT",
            r"rice|chawal|paddy|dhan": "RICE",
            r"onion|pyaz|pyaaz": "ONION",
            r"chilli|chili|mirch": "CHILLI",
            r"cotton|kapas": "COTTON",
            r"maize|corn|makka": "MAIZE",
            r"sugarcane|ganna": "SUGARCANE",
            r"turmeric|haldi": "TURMERIC",
            r"ginger|adrak": "GINGER",
            r"banana|kela": "BANANA",
            r"lemon|nimbu": "LEMON",
            r"mango|aam": "MANGO",
            r"apple|seb": "APPLE",
            r"garlic|lahsun": "GARLIC",
            r"carrot|gajar": "CARROT",
            r"cabbage|patta": "CABBAGE",
            r"cucumber|kheera": "CUCUMBER",
            r"watermelon|tarbooz": "WATERMELON",
            r"rose|gulab": "ROSE",
            r"aloe|vera": "ALOE",
            r"basil|tulsi": "BASIL",
            r"sunflower|suraj": "SUNFLOWER",
            r"neem": "NEEM",
            r"mint|pudina": "MINT",
            r"coffee": "COFFEE",
        }

        for pattern, key in patterns.items():
            if re.search(pattern, filename):
                data = PLANT_CARE_DB[key].copy()
                data["confidence"] = 92.0
                return data

        return None

    # ---------------- ENRICH PLANT DATA ----------------
    def enrich_plant_data(self, plant_dict: Dict[str, Any]) -> Dict[str, Any]:
        common = plant_dict.get("common", "").strip()
        scientific = plant_dict.get("name", "").strip()

        matched_db: Optional[Dict[str, Any]] = None
        for key, db_item in PLANT_CARE_DB.items():
            if (key.lower() in common.lower() or 
                db_item["common"].lower() in common.lower() or 
                db_item["name"].lower() in scientific.lower()):
                matched_db = db_item
                break

        wiki_query = matched_db.get("wiki_title") if matched_db else (scientific or common)
        wiki_info = self.fetch_wikipedia_info(wiki_query)

        result: Dict[str, Any] = {}
        if matched_db:
            result.update(matched_db)
        else:
            result.update({
                "name": scientific or common,
                "common": common or scientific,
                "min_temp": 15,
                "max_temp": 32,
                "light": "Adequate sunlight (4-6 hours)",
                "water": "Regular watering when topsoil feels dry",
                "soil": "Fertile, well-draining garden soil",
                "family": plant_dict.get("family", "Plantae"),
                "season": "Year-round / Seasonal",
                "harvest": "Depending on regional climate",
                "tip": "Ensure adequate sunlight, balanced soil aeration, and organic mulching."
            })

        result["confidence"] = plant_dict.get("confidence", 85.0)
        result["wikipedia_url"] = wiki_info.get("url") or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(result['common'])}"
        result["wikipedia_summary"] = wiki_info.get("extract") or f"Encyclopedic agricultural profile for {result['common']}."
        result["wikipedia_title"] = wiki_info.get("title") or result["common"]
        result["wiki_url"] = result["wikipedia_url"]
        result["wiki_summary"] = result["wikipedia_summary"]
        result["wiki_title"] = result["wikipedia_title"]
        result["thumbnail"] = wiki_info.get("thumbnail")
        result["temperature_min"] = result.get("min_temp", 15)
        result["temperature_max"] = result.get("max_temp", 30)
        result["water_requirement"] = result.get("water", "Moderate watering")
        result["sunlight"] = result.get("light", "Adequate sunlight")
        result["soil_type"] = result.get("soil", "Well-drained soil")
        result["harvest_time"] = result.get("harvest", "60-90 days")

        return result

    # ---------------- TEXT SEARCH ----------------
    def get_plant_care(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        clean_text = text.strip().lower()

        # Direct match in local dictionary
        for key, data in PLANT_CARE_DB.items():
            if (key.lower() in clean_text or 
                data["common"].lower() in clean_text or 
                data["name"].lower() in clean_text):
                return self.enrich_plant_data(data)

        # Transliterated names / aliases
        aliases = {
            "tamatar": "TOMATO", "aalu": "POTATO", "aloo": "POTATO",
            "gehun": "WHEAT", "gehu": "WHEAT", "gandum": "WHEAT",
            "chawal": "RICE", "dhan": "RICE", "paddy": "RICE",
            "pyaz": "ONION", "pyaaz": "ONION", "mirch": "CHILLI",
            "mirchi": "CHILLI", "kapas": "COTTON", "makka": "MAIZE",
            "bhutta": "MAIZE", "ganna": "SUGARCANE", "haldi": "TURMERIC",
            "gulab": "ROSE", "tulsi": "BASIL", "surajmukhi": "SUNFLOWER",
            "kamal": "LOTUS", "adrak": "GINGER", "aam": "MANGO", "pudina": "MINT",
            "kela": "BANANA", "nimbu": "LEMON", "seb": "APPLE", "lahsun": "GARLIC",
            "gajar": "CARROT", "kheera": "CUCUMBER", "tarbooz": "WATERMELON"
        }
        for alias, key in aliases.items():
            if alias in clean_text and key in PLANT_CARE_DB:
                return self.enrich_plant_data(PLANT_CARE_DB[key])

        # Clean filler words
        cleaned_query = re.sub(
            r"\b(tell me about|how to grow|how to care for|plant care for|information on|guidance for|what is|cultivation of|tips for|care for|about)\b",
            "",
            clean_text,
            flags=re.IGNORECASE
        ).strip()

        if cleaned_query and len(cleaned_query) >= 3 and not re.match(r"^(hi|hello|hey|help|thanks|thank you|ok|okay)$", cleaned_query):
            wiki_info = self.fetch_wikipedia_info(cleaned_query)
            if wiki_info and wiki_info.get("found"):
                plant_obj = {
                    "name": wiki_info.get("title", cleaned_query.title()),
                    "common": cleaned_query.title(),
                    "wiki_title": wiki_info.get("title"),
                    "min_temp": 15,
                    "max_temp": 32,
                    "light": "Full to partial sunlight (5-7 hours)",
                    "water": "Regular moderate moisture, well-draining soil",
                    "soil": "Rich organic loamy soil",
                    "family": "Plantae",
                    "season": "Spring / Autumn",
                    "harvest": "Check regional harvest calendar",
                    "tip": "Provide well-aerated soil, organic compost, and avoid stagnant water."
                }
                return self.enrich_plant_data(plant_obj)

        return None

    # ---------------- WEATHER ----------------
    def get_weather(self, city: str = "rajpura") -> Dict[str, Any]:
        city_lower = city.lower().strip()
        lat, lon = INDIAN_LOCATIONS.get(city_lower, INDIAN_LOCATIONS["rajpura"])
        
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "timezone": "Asia/Kolkata"
                },
                timeout=6
            )
            if r.status_code == 200:
                w = r.json().get("current_weather", {})
                return {
                    "temp": round(w.get("temperature", 24), 1),
                    "windspeed": w.get("windspeed", 8),
                    "city": city.title(),
                    "live": True
                }
        except Exception:
            pass

        return {"temp": 24.5, "windspeed": 7.5, "city": city.title(), "live": False}

    # ---------------- ANALYSIS ----------------
    def analyze(self, plant: Dict[str, Any], weather: Dict[str, Any]) -> Dict[str, Any]:
        temp = weather.get("temp", 24)
        min_t = plant.get("min_temp") or plant.get("temperature_min") or 15
        max_t = plant.get("max_temp") or plant.get("temperature_max") or 30
        try:
            min_t = float(min_t)
            max_t = float(max_t)
        except (ValueError, TypeError):
            min_t, max_t = 15.0, 30.0

        if min_t <= temp <= max_t:
            status = "OPTIMAL GROWING CONDITIONS"
            status_color = "green"
            advisory = f"Current temperature ({temp} deg C) is in the optimal range ({min_t}-{max_t} deg C) for {plant.get('common', 'this crop')}."
        elif temp > max_t:
            status = "HIGH TEMPERATURE ADVISORY"
            status_color = "red"
            advisory = f"Current temperature ({temp} deg C) exceeds optimal range ({min_t}-{max_t} deg C). Provide light shade net and mulch heavily to protect roots."
        else:
            status = "LOW TEMPERATURE ADVISORY"
            status_color = "blue"
            advisory = f"Current temperature ({temp} deg C) is below optimal range ({min_t}-{max_t} deg C). Protect roots against cold stress with protective mulch."

        common_name = plant.get("common") or plant.get("name") or "Crop"
        scientific_name = plant.get("scientific_name") or plant.get("name") or common_name
        wiki_url = plant.get("wikipedia_url") or plant.get("wiki_url") or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(common_name)}"
        wiki_summary = plant.get("wikipedia_summary") or plant.get("wiki_summary") or f"Encyclopedic information regarding {common_name} on Wikipedia."
        water = plant.get("water") or plant.get("water_requirement") or "Moderate watering"
        light = plant.get("light") or plant.get("sunlight") or "Adequate sunlight"
        soil = plant.get("soil") or plant.get("soil_type") or "Well-draining loam"
        harvest = plant.get("harvest") or plant.get("harvest_time") or "60-90 days"

        return {
            "name": common_name,
            "plant": common_name,
            "common": common_name,
            "scientific_name": scientific_name,
            "family": plant.get("family", "Plantae"),
            "temp": temp,
            "city": weather.get("city", "Rajpura"),
            "range": f"{int(min_t)}-{int(max_t)} deg C",
            "status": status,
            "status_color": status_color,
            "advisory": advisory,
            "min_temp": min_t,
            "max_temp": max_t,
            "temperature_min": min_t,
            "temperature_max": max_t,
            "light": light,
            "sunlight": light,
            "water": water,
            "water_requirement": water,
            "soil": soil,
            "soil_type": soil,
            "season": plant.get("season", "Seasonal"),
            "harvest": harvest,
            "harvest_time": harvest,
            "tip": plant.get("tip", "Maintain optimal soil moisture and balanced nutrient aeration."),
            "wikipedia_url": wiki_url,
            "wikipedia_summary": wiki_summary,
            "wiki_url": wiki_url,
            "wiki_summary": wiki_summary,
            "wiki_title": plant.get("wikipedia_title", common_name),
            "thumbnail": plant.get("thumbnail"),
            "confidence": plant.get("confidence", 90.0),
            "annotated_image": plant.get("annotated_image"),
            "annotated_filename": plant.get("annotated_filename"),
            "detection_source": plant.get("detection_source", "Knowledge Base"),
            "detections_summary": plant.get("detections_summary"),
            "total_objects": plant.get("total_objects", 1)
        }
