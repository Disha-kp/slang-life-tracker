import nltk
from nltk.corpus import words, wordnet
from nltk.sentiment import SentimentIntensityAnalyzer
import ssl

# Fix for NLTK download SSL/certificate issues on some machines
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Ensure necessary NLTK data is downloaded
try:
    nltk.data.find('corpora/words')
except LookupError:
    nltk.download('words')

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

try:
    nltk.data.find('corpora/wordnet.zip')
except LookupError:
    nltk.download('wordnet')

# Initialize resources
ENGLISH_VOCAB = set(words.words())
sia = SentimentIntensityAnalyzer()

NICHE_SUBREDDITS = ['london', 'ukdrill']

def is_slang(word, context, subreddit):
    """
    Determines if a word is slang based on corpus presence, sentiment intensity, and origin.
    
    Args:
        word (str): The word to check.
        context (str): The sentence/comment containing the word.
        subreddit (str): The subreddit where it was found.
        
    Returns:
        dict: {'is_slang': bool, 'score': float, 'reasons': list}
    """
    score = 0.1 # Base score
    reasons = []
    
    word_lower = word.lower()
    
    # 1. Corpus Check
    # If the word is NOT in standard English dictionary, likely slang or neologism.
    if word_lower not in ENGLISH_VOCAB and not wordnet.synsets(word_lower):
        score += 0.4
        reasons.append("Not in standard dictionary")
    else:
        # Even if in dictionary, might be slang usage (e.g., 'cooked', 'cap')
        # This is hard to detect without context-aware embeddings, but we rely on other factors.
        score -= 0.1 

    # 2. Intensity/Sentiment Check (VADER)
    # Slang often appears in high-intensity (emotional) contexts.
    if context:
        sentiment = sia.polarity_scores(context)
        # Compound score ranges -1 to 1. Check absolute intensity.
        if abs(sentiment['compound']) > 0.5:
            score += 0.2
            reasons.append(f"High sentiment intensity ({sentiment['compound']:.2f})")
    
    # 3. Subreddit/Context Check
    if subreddit in NICHE_SUBREDDITS:
        score += 0.3
        reasons.append("Found in Niche Subreddit")
        
    # 4. Length heuristic (removed - not useful for now)
    pass

    # Cap score at 1.0
    score = min(score, 1.0)
    
    # Decision
    is_slang_val = score > 0.6 # Threshold from plan was 0.7, but code logic sums to max ~0.9. 
                               # 0.4 (corpus) + 0.2 (sentiment) + 0.3 (niche) = 0.9.
                               # 0.6 seems reasonable for "Likely Slang".
    
    return {
        'is_slang': is_slang_val,
        'score': round(score, 2),
        'reasons': reasons
    }

if __name__ == "__main__":
    # Quick manual test
    print(is_slang("rizz", "This guy has insane rizz", "ukdrill"))
    print(is_slang("friend", "He is my best friend", "AskReddit"))
