import sys
import pandas as pd
from sqlalchemy import create_engine

def load_data(messages_filepath, categories_filepath):
    """
    Load data from CSV files and merge them.
    
    :param messages_filepath: Path to messages CSV file.
    :param categories_filepath: Path to categories CSV file.
    :return: Merged DataFrame.
    """
    messages = pd.read_csv(messages_filepath)
    categories = pd.read_csv(categories_filepath)
    df = pd.merge(messages, categories, on='id')
    return df

def clean_data(df):
    """
    Clean and transform the merged DataFrame.
    
    :param df: Merged DataFrame.
    :return: Cleaned DataFrame.
    """
    categories = df['categories'].str.split(pat=';', expand=True)
    row = categories.iloc[0]
    category_colnames = row.apply(lambda x: x[:-2])
    categories.columns = category_colnames
    categories = categories.applymap(lambda x: int(x[-1]))
    
    df = df.drop('categories', axis=1)
    df = pd.concat([df, categories], axis=1)
    df.drop_duplicates(inplace=True)
    df = df.drop('child_alone', axis=1)
    df['related'] = df['related'].map(lambda x: 1 if x == 2 else x)
    
    return df

def save_data(df, database_filename):
    """
    Save cleaned data to an SQLite database.
    
    :param df: Cleaned DataFrame.
    :param database_filename: Filename for the SQLite database.
    :return: None
    """
    engine = create_engine(f'sqlite:///{database_filename}')
    df.to_sql('DisasterResponse_table', engine, index=False, if_exists='replace')

def main():
    if len(sys.argv) == 4:
        messages_filepath, categories_filepath, database_filepath = sys.argv[1:]

        print(f'Loading data...\n    MESSAGES: {messages_filepath}\n    CATEGORIES: {categories_filepath}')
        df = load_data(messages_filepath, categories_filepath)

        print('Cleaning data...')
        df = clean_data(df)

        print(f'Saving data...\n    DATABASE: {database_filepath}')
        save_data(df, database_filepath)

        print('Cleaned data saved to the database!')
    else:
        print('Please provide the filepaths of the messages and categories datasets as the first and second argument respectively, as well as the filepath of the database to save the cleaned data to as the third argument.\n\nExample: python process_data.py disaster_messages.csv disaster_categories.csv DisasterResponse.db')

if __name__ == '__main__':
    main()
