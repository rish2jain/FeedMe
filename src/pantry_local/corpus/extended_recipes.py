"""Additional household recipes to reach the 50+ v0 corpus target."""

from __future__ import annotations

from ..models import Recipe, RecipeIngredient as RI, FORMAT_GRAVY, FORMAT_DRY, FORMAT_ONE_POT
from ..ontology import (
    PROTEIN_DAL, PROTEIN_PANEER, PROTEIN_CHANA, PROTEIN_RAJMA,
    PROTEIN_TOFU, PROTEIN_YOGURT,
)
from .helpers import _r

EXTENDED_RECIPES: list[Recipe] = [
    _r(id="moong-dal", title="Moong Dal", ingredients=[
        RI("moong dal", 1, "cup"), RI("turmeric", 0.5, "tsp"), RI("cumin seeds", 1, "tsp"),
        RI("garlic", 3, "cloves", stage="tadka"), RI("salt", 1, "tsp", stage="tadka"),
    ], steps=["Boil moong dal.", "Pull toddler portion.", "Tadka with cumin and garlic."],
       prep_minutes=5, active_minutes=18, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.4, tags=["weeknight"], source="household"),
    _r(id="chana-dal", title="Chana Dal", ingredients=[
        RI("chana dal", 1, "cup"), RI("turmeric", 0.5, "tsp"), RI("onion", 1, "medium"),
        RI("tomato", 1, "medium"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Cook chana dal.", "Pull toddler portion.", "Add masala and salt."],
       prep_minutes=5, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.5, tags=["weeknight"], source="household"),
    _r(id="methi-aloo", title="Methi Aloo", ingredients=[
        RI("fenugreek leaves", 2, "cups", form="chopped"), RI("potato", 2, "medium", form="cubed"),
        RI("turmeric", 0.5, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Saute potato and methi.", "Pull toddler portion.", "Add salt."],
       prep_minutes=10, active_minutes=18, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["use-first"], source="household"),
    _r(id="shobji-dalna", title="Light Shobji Dalna", ingredients=[
        RI("potato", 2, "medium"), RI("cauliflower", 0.5, "small"), RI("peas", 0.5, "cup"),
        RI("panch phoron", 1, "tsp"), RI("turmeric", 0.5, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Temper panch phoron.", "Cook vegetables.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=10, active_minutes=22, cooking_format=FORMAT_GRAVY, protein_class=None,
       toddler_fork_step=2, leftover_yield=1.2, tags=["comfort"], source="household"),
    _r(id="aloo-posto", title="Aloo Posto", ingredients=[
        RI("poppy seeds", 3, "tbsp"), RI("potato", 3, "medium"), RI("green chili", 1, "whole", stage="finish"),
        RI("mustard oil", 2, "tbsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Grind posto.", "Cook potato.", "Pull toddler portion.", "Finish with chili and salt."],
       prep_minutes=10, active_minutes=20, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["bengali"], source="household"),
    _r(id="shukto", title="Mild Shukto", ingredients=[
        RI("bitter gourd", 1, "medium"), RI("potato", 1, "medium"), RI("drumstick", 2, "pieces"),
        RI("milk", 0.5, "cup"), RI("turmeric", 0.25, "tsp"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Par-boil vegetables.", "Pull very mild toddler portion early.", "Simmer with milk."],
       prep_minutes=15, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["bengali"], source="household"),
    _r(id="potol-posto", title="Potol Posto", ingredients=[
        RI("pointed gourd", 6, "whole"), RI("poppy seeds", 2, "tbsp"), RI("turmeric", 0.25, "tsp"),
        RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Cook potol.", "Pull toddler portion.", "Add posto paste and salt."],
       prep_minutes=10, active_minutes=18, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["bengali"], source="household"),
    _r(id="labra", title="Bengali Labra", ingredients=[
        RI("pumpkin", 2, "cups", form="cubed"), RI("potato", 1, "medium"), RI("eggplant", 1, "small"),
        RI("turmeric", 0.5, "tsp"), RI("panch phoron", 1, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Temper and stew vegetables.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=12, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.3, tags=["bengali"], source="household"),
    _r(id="mishti-kumro", title="Mishti Kumro", ingredients=[
        RI("pumpkin", 3, "cups", form="cubed"), RI("mustard oil", 1, "tbsp"), RI("turmeric", 0.5, "tsp"),
        RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Saute pumpkin.", "Pull toddler portion.", "Finish with salt."],
       prep_minutes=8, active_minutes=15, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["side"], source="household"),
    _r(id="tofu-jhol", title="Tofu Jhol", ingredients=[
        RI("tofu", 300, "g", form="cubed"), RI("potato", 1, "medium"), RI("tomato", 1, "medium"),
        RI("turmeric", 0.5, "tsp"), RI("cumin powder", 1, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Build light jhol.", "Add tofu and potato.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=10, active_minutes=20, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_TOFU,
       toddler_fork_step=1, leftover_yield=1.2, tags=["comfort"], source="household"),
    _r(id="paneer-tikka-home", title="Home Paneer Tikka Bowl", ingredients=[
        RI("paneer", 250, "g"), RI("yogurt", 0.5, "cup"), RI("turmeric", 0.25, "tsp"),
        RI("coriander powder", 1, "tsp"), RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Marinate paneer.", "Pull toddler portion unspiced.", "Broil or pan-sear."],
       prep_minutes=15, active_minutes=12, cooking_format=FORMAT_DRY, protein_class=PROTEIN_PANEER,
       toddler_fork_step=1, leftover_yield=1.0, tags=["quick"], source="household"),
    _r(id="tofu-pepper-fry", title="Tofu Pepper Fry", ingredients=[
        RI("tofu", 300, "g"), RI("bell pepper", 2, "whole"), RI("soy sauce", 1, "tbsp", stage="finish"),
        RI("black pepper", 0.5, "tsp", stage="finish"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Stir-fry tofu and peppers.", "Pull toddler portion before soy.", "Finish."],
       prep_minutes=10, active_minutes=12, cooking_format=FORMAT_DRY, protein_class=PROTEIN_TOFU,
       toddler_fork_step=1, leftover_yield=1.0, tags=["quick"], source="household"),
    _r(id="veg-korma", title="Vegetable Korma", ingredients=[
        RI("cauliflower", 0.5, "small"), RI("carrot", 2, "medium"), RI("peas", 0.5, "cup"),
        RI("yogurt", 0.5, "cup"), RI("cashew", 0.25, "cup", form="paste"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Cook vegetables.", "Pull toddler portion.", "Finish with yogurt cashew base."],
       prep_minutes=12, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_YOGURT,
       toddler_fork_step=1, leftover_yield=1.3, tags=["weekend"], source="household"),
    _r(id="malai-kofta-style", title="Malai Kofta-style Gravy", ingredients=[
        RI("potato", 2, "medium"), RI("paneer", 150, "g"), RI("tomato", 2, "medium"),
        RI("cream", 0.25, "cup", stage="finish"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Make kofta.", "Pull toddler portion plain.", "Simmer in tomato gravy."],
       prep_minutes=20, active_minutes=30, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_PANEER,
       toddler_fork_step=1, leftover_yield=1.2, tags=["weekend"], source="household"),
    _r(id="pav-bhaji", title="Pav Bhaji", ingredients=[
        RI("potato", 3, "medium"), RI("tomato", 3, "medium"), RI("peas", 0.5, "cup"),
        RI("pav bhaji masala", 2, "tbsp"), RI("butter", 2, "tbsp", stage="finish"),
        RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Mash bhaji.", "Pull toddler portion before butter.", "Toast pav separately."],
       prep_minutes=15, active_minutes=25, cooking_format=FORMAT_ONE_POT, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.5, tags=["weekend"], source="household"),
    _r(id="chole", title="Punjabi Chole", ingredients=[
        RI("chickpeas", 2, "cups", form="cooked"), RI("onion", 2, "medium"), RI("tomato", 2, "medium"),
        RI("chole masala", 2, "tbsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Build chole masala.", "Pull toddler portion.", "Simmer chickpeas."],
       prep_minutes=10, active_minutes=28, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_CHANA,
       toddler_fork_step=1, leftover_yield=1.5, tags=["protein"], source="household"),
    _r(id="lobia", title="Lobia Curry", ingredients=[
        RI("black-eyed peas", 1.5, "cups", form="cooked"), RI("onion", 1, "medium"),
        RI("tomato", 1, "medium"), RI("turmeric", 0.5, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Cook lobia curry.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=8, active_minutes=22, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.4, tags=["protein"], source="household"),
    _r(id="sambar", title="Quick Sambar", ingredients=[
        RI("toor dal", 0.75, "cup"), RI("drumstick", 2, "pieces"), RI("tamarind", 1, "tsp"),
        RI("sambar powder", 2, "tbsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Cook dal and vegetables.", "Pull toddler portion.", "Finish with sambar powder."],
       prep_minutes=10, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.3, tags=["south"], source="household"),
    _r(id="lemon-rice", title="Lemon Rice", ingredients=[
        RI("basmati rice", 2, "cups", form="cooked"), RI("lemon", 1, "whole"), RI("mustard seeds", 1, "tsp"),
        RI("turmeric", 0.25, "tsp"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Temper spices.", "Mix rice.", "Pull toddler portion.", "Add lemon and salt."],
       prep_minutes=5, active_minutes=10, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["quick"], source="household"),
    _r(id="tamarind-rice", title="Puliyodarai-style Rice", ingredients=[
        RI("basmati rice", 2, "cups", form="cooked"), RI("tamarind", 2, "tbsp"), RI("peanut", 2, "tbsp"),
        RI("mustard seeds", 1, "tsp"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Make tamarind paste.", "Pull toddler portion mild.", "Mix with rice."],
       prep_minutes=8, active_minutes=12, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["leftover"], source="household"),
    _r(id="jeera-rice", title="Jeera Rice", ingredients=[
        RI("basmati rice", 1.5, "cups"), RI("cumin seeds", 2, "tsp"), RI("ghee", 1, "tbsp"),
        RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Temper cumin in ghee.", "Cook rice.", "Pull toddler portion.", "Salt lightly."],
       prep_minutes=5, active_minutes=18, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["side"], source="household"),
    _r(id="roti-night", title="Roti with Dal and Sabzi", ingredients=[
        RI("atta", 2, "cups"), RI("masoor dal", 0.75, "cup"), RI("mixed vegetables", 2, "cups"),
        RI("turmeric", 0.5, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Roll rotis.", "Cook dal and sabzi.", "Pull toddler portions.", "Serve."],
       prep_minutes=15, active_minutes=30, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=2, leftover_yield=1.2, tags=["staple"], source="household"),
    _r(id="paratha-aloo", title="Aloo Paratha", ingredients=[
        RI("atta", 2, "cups"), RI("potato", 3, "medium", form="mashed"), RI("cumin seeds", 1, "tsp"),
        RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Make filling.", "Pull toddler portion.", "Roll and cook parathas."],
       prep_minutes=15, active_minutes=20, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["weekend"], source="household"),
    _r(id="poha", title="Vegetable Poha", ingredients=[
        RI("poha", 2, "cups"), RI("onion", 1, "medium"), RI("peas", 0.25, "cup"),
        RI("mustard seeds", 1, "tsp"), RI("turmeric", 0.25, "tsp"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Rinse poha.", "Temper and mix.", "Pull toddler portion.", "Salt lightly."],
       prep_minutes=8, active_minutes=10, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["breakfast"], source="household"),
    _r(id="upma", title="Vegetable Upma", ingredients=[
        RI("semolina", 1, "cup"), RI("onion", 1, "medium"), RI("peas", 0.25, "cup"),
        RI("mustard seeds", 1, "tsp"), RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Roast rava.", "Cook upma.", "Pull toddler portion.", "Finish."],
       prep_minutes=8, active_minutes=12, cooking_format=FORMAT_ONE_POT, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["breakfast"], source="household"),
    _r(id="idli-sambhar", title="Idli with Sambar", ingredients=[
        RI("idli batter", 2, "cups"), RI("toor dal", 0.5, "cup"), RI("drumstick", 1, "piece"),
        RI("sambar powder", 1, "tbsp"), RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Steam idli.", "Cook sambar.", "Pull toddler portions.", "Serve."],
       prep_minutes=10, active_minutes=25, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.0, tags=["weekend"], source="household"),
    _r(id="dosa-potato", title="Masala Dosa", ingredients=[
        RI("dosa batter", 2, "cups"), RI("potato", 2, "medium", form="mashed"), RI("onion", 1, "medium"),
        RI("mustard seeds", 1, "tsp"), RI("turmeric", 0.25, "tsp"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Make masala.", "Pull toddler portion.", "Crisp dosas."],
       prep_minutes=15, active_minutes=20, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["weekend"], source="household"),
    _r(id="uttapam", title="Vegetable Uttapam", ingredients=[
        RI("dosa batter", 2, "cups"), RI("onion", 1, "medium", form="finely chopped"),
        RI("tomato", 1, "medium", form="finely chopped"), RI("salt", 0.5, "tsp", stage="finish"),
    ], steps=["Top batter with veg.", "Pull toddler portion.", "Cook uttapam."],
       prep_minutes=8, active_minutes=12, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["weekend"], source="household"),
    _r(id="veg-biryani", title="Vegetable Biryani", ingredients=[
        RI("basmati rice", 2, "cups"), RI("mixed vegetables", 3, "cups"), RI("yogurt", 0.5, "cup"),
        RI("biryani masala", 2, "tbsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Par-cook rice.", "Layer with veg.", "Pull toddler portion.", "Dum and serve."],
       prep_minutes=20, active_minutes=35, cooking_format=FORMAT_ONE_POT, protein_class=PROTEIN_YOGURT,
       toddler_fork_step=1, leftover_yield=1.6, tags=["weekend"], source="household"),
    _r(id="tahri", title="Vegetable Tahri", ingredients=[
        RI("basmati rice", 1.5, "cups"), RI("potato", 1, "medium"), RI("peas", 0.5, "cup"),
        RI("turmeric", 0.5, "tsp"), RI("cumin seeds", 1, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Temper spices.", "Cook rice with vegetables.", "Pull toddler portion."],
       prep_minutes=10, active_minutes=25, cooking_format=FORMAT_ONE_POT, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.4, tags=["one-pot"], source="household"),
    _r(id="dal-makhani-style", title="Dal Makhani-style", ingredients=[
        RI("rajma", 0.5, "cup"), RI("urad dal", 0.5, "cup"), RI("tomato", 2, "medium"),
        RI("butter", 1, "tbsp", stage="finish"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Slow-cook dals.", "Pull toddler portion.", "Finish with butter."],
       prep_minutes=10, active_minutes=40, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_RAJMA,
       toddler_fork_step=1, leftover_yield=1.6, tags=["weekend"], source="household"),
    _r(id="palak-dal", title="Palak Dal", ingredients=[
        RI("masoor dal", 0.75, "cup"), RI("spinach", 300, "g"), RI("turmeric", 0.5, "tsp"),
        RI("cumin seeds", 1, "tsp"), RI("salt", 1, "tsp", stage="finish"),
    ], steps=["Cook dal with spinach.", "Pull toddler portion.", "Tadka and salt."],
       prep_minutes=8, active_minutes=22, cooking_format=FORMAT_GRAVY, protein_class=PROTEIN_DAL,
       toddler_fork_step=1, leftover_yield=1.4, tags=["iron"], source="household"),
    _r(id="lauki-sabzi", title="Lauki Sabzi", ingredients=[
        RI("bottle gourd", 1, "medium"), RI("tomato", 1, "medium"), RI("turmeric", 0.25, "tsp"),
        RI("cumin seeds", 1, "tsp"), RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Cook lauki.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=8, active_minutes=18, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["light"], source="household"),
    _r(id="turai-sabzi", title="Turai Sabzi", ingredients=[
        RI("ridge gourd", 2, "whole"), RI("onion", 1, "medium"), RI("turmeric", 0.25, "tsp"),
        RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Saute turai.", "Pull toddler portion.", "Finish."],
       prep_minutes=8, active_minutes=15, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["side"], source="household"),
    _r(id="kaddu-sabzi", title="Kaddu Sabzi", ingredients=[
        RI("pumpkin", 3, "cups"), RI("fenugreek seeds", 0.5, "tsp"), RI("turmeric", 0.5, "tsp"),
        RI("salt", 0.75, "tsp", stage="finish"),
    ], steps=["Cook pumpkin.", "Pull toddler portion.", "Salt to finish."],
       prep_minutes=8, active_minutes=18, cooking_format=FORMAT_DRY, protein_class=None,
       toddler_fork_step=1, leftover_yield=1.0, tags=["side"], source="household"),
]
