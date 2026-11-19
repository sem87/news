import json

class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process_data(self):
        # Check if 'age' key exists in the dictionary
        if 'age' in self.data:
            age = self.data['age']
        else:
            raise KeyError("Key 'age' not found in the dictionary")

        # Perform some processing on the age
        processed_age = age * 2

        return processed_age

    def save_to_json(self, filename: str):
        # Process the data first
        processed_age = self.process_data()

        # Save the processed data to a JSON file
        with open(filename, 'w') as json_file:
            json.dump({'processed_age': processed_age}, json_file, indent=4)

if __name__ == '__main__':
    # Example data
    data = {'name': 'John', 'age': 30}

    # Create an instance of DataProcessor
    processor = DataProcessor(data)

    # Process the data
    processed_age = processor.process_data()

    # Save the processed data to a JSON file
    processor.save_to_json('processed_data.json')