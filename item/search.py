import spacy
import numpy as np

from textblob import TextBlob
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

from .models import Item


CUSTOM_SYNONYMS = {
    'head hurt': ['headache', 'migraine', 'cephalalgia'],
    'pain relief': ['analgesic', 'painkiller', 'pain relief', 'pain reliever'],
    'stomach ache': ['abdominal pain', 'stomach pain', 'gastric pain', 'belly ache'],
    'fever': ['pyrexia', 'high temperature', 'febrile', 'feverishness'],
    'cold': ['common cold', 'upper respiratory infection', 'nasopharyngitis'],
    'cough': ['tussis', 'dry cough', 'productive cough'],
    'sore throat': ['pharyngitis', 'throat pain', 'throat irritation'],
    'runny nose': ['rhinorrhea', 'nasal discharge'],
    'heartburn': ['acid reflux', 'gastroesophageal reflux', 'GERD'],
    'nausea': ['queasiness', 'sickness', 'upset stomach'],
    'vomiting': ['emesis', 'throwing up'],
    'diarrhea': ['loose stools', 'frequent bowel movements', 'dysentery'],
    'constipation': ['infrequent bowel movements', 'difficulty passing stools'],
    'back pain': ['lumbago', 'lower back pain', 'spinal discomfort'],
    'joint pain': ['arthralgia', 'joint discomfort', 'joint stiffness'],
    'muscle pain': ['myalgia', 'muscle ache', 'muscle soreness'],
    'dizziness': ['vertigo', 'lightheadedness', 'faintness'],
    'allergies': ['hypersensitivity', 'allergic reaction'],
    'rash': ['dermatitis', 'skin irritation', 'hives', 'urticaria'],
    'fatigue': ['tiredness', 'exhaustion', 'lethargy'],
    'insomnia': ['sleeplessness', 'difficulty sleeping', 'sleep disorder'],
    'anxiety': ['nervousness', 'worry', 'anxiety disorder'],
    'depression': ['low mood', 'clinical depression', 'major depressive disorder'],
    'high blood pressure': ['hypertension', 'elevated blood pressure'],
    'low blood pressure': ['hypotension', 'low BP'],
    'diabetes': ['high blood sugar', 'hyperglycemia', 'diabetic condition'],
    'obesity': ['overweight', 'excess weight', 'adiposity'],
    'infection': ['bacterial infection', 'viral infection', 'fungal infection'],
    'asthma': ['bronchial asthma', 'reactive airway disease'],
    'arthritis': ['joint inflammation', 'rheumatoid arthritis', 'osteoarthritis'],
    'allergic rhinitis': ['hay fever', 'nasal allergies'],
    'high cholesterol': ['hypercholesterolemia', 'elevated cholesterol'],
    'flu': ['influenza', 'viral flu'],
    'heart attack': ['myocardial infarction', 'cardiac arrest'],
    'stroke': ['cerebrovascular accident', 'brain attack'],
    'cancer': ['malignancy', 'tumor', 'neoplasm'],
    'kidney stones': ['renal calculi', 'nephrolithiasis'],
    'urinary tract infection': ['UTI', 'bladder infection', 'cystitis'],
    'skin infection': ['cellulitis', 'dermal infection'],
    'bronchitis': ['chest cold', 'bronchial infection'],
    'pneumonia': ['lung infection', 'pulmonary infection'],
    'anemia': ['low hemoglobin', 'iron deficiency', 'blood deficiency'],
    'thyroid disorder': ['hypothyroidism', 'hyperthyroidism', 'thyroid disease'],
    'menstrual pain': ['dysmenorrhea', 'period pain', 'menstrual cramps'],
    'birth control': ['contraception', 'family planning', 'contraceptive'],
    'pregnancy': ['gestation', 'expecting', 'carrying a child'],
    'asthma attack': ['bronchospasm', 'acute asthma exacerbation'],
    'eczema': ['atopic dermatitis', 'chronic skin inflammation'],
    'acne': ['pimples', 'zits', 'acne vulgaris'],
    'diabetic neuropathy': ['nerve pain in diabetes', 'diabetic nerve damage'],
    'COPD': ['chronic obstructive pulmonary disease', 'chronic bronchitis', 'emphysema'],
    'gout': ['gouty arthritis', 'uric acid crystals', 'joint inflammation due to gout'],
    'osteoporosis': ['bone loss', 'reduced bone density', 'brittle bones'],
    'glaucoma': ['eye pressure', 'optic nerve damage', 'eye disease'],
    'cataract': ['cloudy lens', 'lens opacity', 'eye cataract'],
    'migraine': ['severe headache', 'migraine attack', 'vascular headache'],
    'food poisoning': ['gastroenteritis', 'stomach bug', 'foodborne illness'],
    'autism': ['autism spectrum disorder', 'ASD'],
    'alzheimer': ['alzheimer’s disease', 'dementia', 'memory loss'],
    'parkinson': ['parkinson’s disease', 'PD', 'neurodegenerative disorder'],
    'epilepsy': ['seizure disorder', 'convulsive disorder'],
    'bipolar disorder': ['manic depression', 'bipolar affective disorder'],
    'schizophrenia': ['psychotic disorder', 'schizoaffective disorder'],
    'irritable bowel syndrome': ['IBS', 'spastic colon', 'irritable colon'],
    'liver disease': ['hepatic disease', 'cirrhosis', 'hepatitis'],
    'ulcer': ['peptic ulcer', 'gastric ulcer', 'stomach ulcer'],
    'herpes': ['herpes simplex', 'HSV', 'cold sores', 'genital herpes'],
    'HIV': ['human immunodeficiency virus', 'AIDS virus', 'HIV infection'],
    'malaria': ['plasmodium infection', 'mosquito-borne disease'],
    'tuberculosis': ['TB', 'mycobacterium tuberculosis infection'],
    'arthritis pain': ['joint pain', 'arthralgia', 'inflammation pain'],
    'ringworm': ['tinea', 'fungal skin infection'],
    'warts': ['verrucae', 'HPV warts', 'skin growth'],
    'ear infection': ['otitis media', 'otitis externa', 'earache'],
    'allergy': ['hypersensitivity', 'allergic response', 'immune reaction'],
    'antibiotic': ['antibacterial', 'antimicrobial', 'infection treatment'],
    'painkiller': ['analgesic', 'pain reliever', 'pain relief medication'],
    'antiviral': ['virus treatment', 'viral infection medication'],
    'antifungal': ['fungus treatment', 'fungal infection medication'],
    'antidepressant': ['depression treatment', 'mood stabilizer', 'SSRI'],
}

nlp = spacy.load("en_core_web_sm")


def correct_text(query):
    blob = TextBlob(query)
    corrected_query = str(blob.correct())

    return corrected_query


def perform_search(query):
    filtered_items = []
    for item in Item.objects.all():
        if item.name.lower() in query or item.category.name.lower() in query:
            filtered_items.append(item)
        else:
            split_description = item.description.lower().split()
            for word in split_description:
                if word in query:
                    filtered_items.append(item)
                    break

    return filtered_items


def preprocess_query(query):
    tokens = word_tokenize(query)
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token.lower()) for token in tokens if
              token.isalpha() and token not in stopwords.words('english')]
    return ' '.join(tokens)


def expand_query_with_synonyms(query):
    synonyms = set()

    query = query.lower()

    for phrase, syns in CUSTOM_SYNONYMS.items():
        if phrase in query:
            synonyms.update(syns)
            query = query.replace(phrase, "")

    words = query.split()

    for word in words:
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name().replace('_', ' '))
    if not synonyms:
        synonyms = words
    return ' '.join(synonyms)


def semantic_search(query, items):
    query_vector = nlp(query).vector
    results = []
    for item in items:
        item_vector = nlp(item.name.lower()).vector
        similarity = query_vector.dot(item_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(item_vector))
        results.append((item, similarity, 'n'))

    results.sort(key=lambda x: x[1], reverse=True)

    return [result[0] for result in results]


def perform_nlp_search(query):
    query = correct_text(query)
    preprocessed_query = preprocess_query(query)
    expanded_query = expand_query_with_synonyms(preprocessed_query)
    items = perform_search(expanded_query)
    return semantic_search(query, items)
