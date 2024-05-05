import sys
import pandas as pd
import re
import pickle
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import warnings
from sklearn.metrics import classification_report
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.ensemble import AdaBoostClassifier
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.multioutput import MultiOutputClassifier
from  sklearn.linear_model import LogisticRegression as logestic_regression
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import create_engine
from sklearn.base import BaseEstimator, TransformerMixin
from sentence_transformers import SentenceTransformer
import torch

warnings.filterwarnings("ignore")
nltk.download(['punkt', 'wordnet', 'averaged_perceptron_tagger'])


print("Available GPUs: ", torch.cuda.is_available())


# i implemented a transformer model in this class to extact sentence embeddings and
# it can be used with sklearn piplelines smoothly 
class get_text_embeddings(BaseEstimator, TransformerMixin):
    def __init__(self, transformer_model):
        """
        Initialize the GetTextEmbeddings transformer.
        
        Parameters:
        transformer_model (object): A transformer-based model used for text embedding generation.
        """
        self.transformer_model = transformer_model

    def fit(self, X, y=None):
        """
        Fit method (no actual fitting is performed).
        
        Parameters:
        X (array-like or dataframe): Input data.
        y (array-like or None): Target data (not used).
        
        Returns:
        self (object): The fitted transformer object.
        """
        return self
    
    def transform(self, X):
        """
        Transform input text data into text embeddings.
        
        Parameters:
        X (array-like or dataframe): Input text data.
        
        Returns:
        embeddings (array-like): Text embeddings generated by the transformer model.
        """
        # Reset index to ensure proper alignment
        X.reset_index(drop=True, inplace=True)
        
        # Generate text embeddings using the transformer model
        embeddings = self.transformer_model.encode(X, show_progress_bar=True)
        
        return embeddings
    

def load_data(database_filepath):
    """
    Load data from SQLite database and prepare X, y, and category names.
    
    :param database_filepath: Path to the SQLite database file.
    :return: X - messages, y - categories of the messages, category_names - names of categories.
    """
    engine = create_engine('sqlite:///' + database_filepath)
    df = pd.read_sql_table('DisasterResponse_table', engine)
    
    X = df['message']
    y = df.iloc[:, 4:]
    category_names = y.columns
    return X, y, category_names

def tokenize(text):
    """
    Tokenize and clean text data.
    
    :param text: Raw text.
    :return: Cleaned tokens.
    """
    url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    detected_urls = re.findall(url_regex, text)
    for url in detected_urls:
        text = text.replace(url, "urlplaceholder")
    
    tokens = word_tokenize(text)
    lemmatizer = WordNetLemmatizer()
    
    clean_tokens = []
    for tok in tokens:
        clean_tok = lemmatizer.lemmatize(tok).lower().strip()
        clean_tokens.append(clean_tok)
        
    return clean_tokens

def build_model(transformer_model,clf=logestic_regression()):
    """
    Build a pipeline model with grid search.
    
    :param clf: Classifier model (default: ).
    :return: Grid search model.
    """
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('text_pipeline', Pipeline([
                ('tfidfvect', TfidfVectorizer(tokenizer=tokenize)),
            ])),

         ('embedding_pipeline', Pipeline([
                ('embeddings', get_text_embeddings(transformer_model)),
            ])),


        ])),
        ('clf', MultiOutputClassifier(clf))
    ])
    
    if type(clf).__name__ == "LinearRegression" : 
        parameters = {
        'clf__estimator__max_iter': [100,150],
        'clf__estimator__penalty': ['l1','l2']

        }
    elif type(clf).__name__ == "AdaBoostClassifier":
        parameters = {
        'clf__estimator__learning_rate':[0.05,0.5, 1.0],
        'clf__estimator__n_estimators':[10,20,30]
        }
        
    cv = GridSearchCV(pipeline, param_grid=parameters, cv=5, n_jobs=-1, verbose=3) 
    
    return cv
    
def evaluate_model(model, X_test, Y_test, category_names):
    """
    Evaluate the model's performance.
    
    :param model: Trained model.
    :param X_test: Test messages.
    :param Y_test: Categories for test messages.
    :param category_names: Names of categories.
    :return: None
    """
    Y_pred_test = model.predict(X_test)

    # Threshold for converting to binary (0 or 1)
    threshold = 0.5

    # Convert to binary based on the threshold
    Y_pred_test = [[1 if value >= threshold else 0 for value in inner_list] for inner_list in Y_pred_test]


    print(classification_report(Y_test.values, Y_pred_test, target_names=category_names))
    
def save_model(model, model_filepath):
    """
    Save the trained model to a pickle file.
    
    :param model: Trained model.
    :param model_filepath: Path to save the model.
    :return: None
    """
    with open(model_filepath, 'wb') as f:
        pickle.dump(model, f)

def main():
    if len(sys.argv) == 3:
        database_filepath, model_filepath = sys.argv[1:]
        print(f'Loading data...\n    DATABASE: {database_filepath}')
        X, Y, category_names = load_data(database_filepath)
        

        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)
        
        global transformer_model
        transformer_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

                    
        print('tfidf features shape', TfidfVectorizer(tokenizer=tokenize).fit_transform(X_train[0:2]).shape)
        print('embedding features shape', get_text_embeddings(transformer_model).fit_transform(X_train[0:2]).shape)

        
        print('Building model...')
        model = build_model(transformer_model,clf=AdaBoostClassifier())
        
        print('Training model...')
        model.fit(X_train, Y_train)
        
        print('Evaluating model...')
        evaluate_model(model, X_test, Y_test, category_names)

        print(f'Saving model...\n    MODEL: {model_filepath}')
        save_model(model, model_filepath)

        print('Trained model saved!')

    else:
        print('Please provide the filepath of the disaster messages database '\
              'as the first argument and the filepath of the pickle file to '\
              'save the model to as the second argument. \n\nExample: python '\
              'train_classifier.py ../data/DisasterResponse.db classifier.pkl')

if __name__ == '__main__':
    main()