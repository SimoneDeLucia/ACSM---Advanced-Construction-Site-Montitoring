import base64
from datetime import date, time
import os
from openai import OpenAI

client = OpenAI(api_key="SegretoDiStato")

images_directory = "camera_snapshot"   #questa serve come parametro per il test nel main
giornata_festiva = date.fromisoformat('20250705')
giornata_lavorativa = date.fromisoformat('20250707')

real_timeframes = [(time.fromisoformat('06:00:00'),time.fromisoformat('07:59:59')),(time.fromisoformat('08:00:00'),time.fromisoformat('09:59:59')),(time.fromisoformat('10:00:00'),time.fromisoformat('11:59:59')),(time.fromisoformat('12:00:00'),time.fromisoformat('13:59:59')),(time.fromisoformat('14:00:00'),time.fromisoformat('15:59:59')), (time.fromisoformat('16:00:00'),time.fromisoformat('17:59:59')) ,(time.fromisoformat('18:00:00'),time.fromisoformat('20:00:00'))]

#servono in caso di test
test_timeframes = [(time.fromisoformat('14:00:00'),time.fromisoformat('14:59:59')),(time.fromisoformat('15:00:00'),time.fromisoformat('15:59:59'))]

csv_template = 'Day Timeframe WasCraneUsed NumberOfMoves Weather \n DATE FRAME USED MOVE CONDITION'

class Image():
    def __init__(self,file_path, data, tempo):
        #self.file_path = images_directory + '/' + image
        self.file_path = file_path 
        self.picture_date = date.fromisoformat(data)
        self.picture_time = time.fromisoformat(tempo)
        self.base64_encoded_image = encode_image(self.file_path)

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


#crea il campo content per la call a chatgpt
def create_request_list(day, timeframes_dict):
    requests_list = []
    for timeframe in real_timeframes: 
        images_in_slot = timeframes_dict.get((day, timeframe), [])
        number_of_images = len(images_in_slot)

        # aggiungo le immagini (se ci sono)
        for im in images_in_slot:
            request = {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{im.base64_encoded_image}"
            }
            requests_list.append(request)

        requests_list.append({ "type": "input_text", "text": "The " + str(number_of_images) + " images that I provided were taken from a construction site on " +  str(day) + ' and in the time frame between' + str(timeframe[0]) + ' and ' + str(timeframe[1]) + '.' +
        'The order in which the images were provided is the exact order in which they were taken. Please take every image in the provided timeframe into consideration, each and every one is essential.' + 
        'Your job is to extract the following data from the images:' +
        'If the crane was moved during the timeslot and the amount of times that it moved. To determine the number of moves, starting from the first image and ending with the second to last image, consider if the long horizontal arm of the crane rotates in the next picture. If it does, count it as a movement, otherwise do not; ' +
        'Take note also of the weather condition in the photos. ' 
        })
    requests_list.append({"type": "input_text", "text": 'After analyzing all of the sets of images provided, please add to the response as the last part of the response, preceded by the following string "```", in a format that follows the following csv template,' + 
    'considering each timeframe as a separate line' +
    ' by replacing "DATE" with the date in which the photos were taken, "FRAME" with the time frame in which the photos were taken, ' + 
    ' "USED" with "Yes" if it was used, or with "No" otherwise, "MOVE" with the number of times the crane moved or with "0" if it did not, ' +
    ' "CONDITION" with the weather condition of the photos, which can be: "Sunny", "Rainy", "Stormy", "Cloudy" or "Windy", ' +
    'This is the aforementioned template, remeber to not use a coma to separate the elements, and always include the names of the columns as the first line: ' +
    csv_template})

    return requests_list



#crea una lista delle immagini, che sono composte dal path del file, la data e l'ora dello scatto dai nomi delle immagini. Inoltre si effetua l'encoding in base64 per utilizzo successivo
def create_image_list(images_directory):
    file_paths = os.listdir(images_directory)
    images = []

    for file_path in file_paths:
        split_path = file_path.split('_')
        image_date = split_path[2]
        image_time = split_path[3].split('.')[0]
        full_path = os.path.join(images_directory, file_path)  # path completo
        images.append(Image(full_path,image_date,image_time))
    
    return images



#organizzazione delle foto in un dizionario, raggrupandole per giornata e poi ordinandole secondo l'orario dello scatto
def organize_photos_by_date(images):
    dates_dict = {}
    for image in images:
        if image.picture_date not in dates_dict.keys():
            dates_dict[image.picture_date] = [image]
        else:
            dates_dict[image.picture_date].append(image)

    for date_key in dates_dict:
        dates_dict[date_key].sort(key=lambda x: x.picture_time)

    return dates_dict
    
    
#dal dizionario delle date, si suddivide ancora secondo i timestamp considerati
def orginize_photos_by_timestamp(date_orginized_photos):
    timeframes_dict = {}
    for date_key in date_orginized_photos:
        for image in date_orginized_photos[date_key]:
            for timeframe in real_timeframes:
                if image.picture_time >= timeframe[0] and image.picture_time <= timeframe[1]:
                    if (date_key,timeframe) not in timeframes_dict.keys():
                        timeframes_dict[(date_key, timeframe)] = [image]
                    else:
                        timeframes_dict[(date_key, timeframe)].append(image)

    return timeframes_dict





#genera una richiesta con le immagini di una giornata fornita in formato date, e ritorna la risposta e un file in csv
def generate_chatGPT_response(day,timeframes_dict):

    requests_list = create_request_list(day, timeframes_dict)


    response = client.responses.create(
        model="gpt-4.1-2025-04-14",  
        input=[
            {
                "role": "user",
                "content": requests_list,
            }
        ],
        temperature=0.0
    )

    print(response.output_text)

    response_text_split = response.output_text.split("```") #questo carattere separa l'output testuale di cahtgpt con il csv


    return response_text_split[1] #corrisponde al csv
    
    


def image_detection(day, image_folder,network,camera):  
    images_path = os.path.join(image_folder, network, camera)
    if not os.path.exists(images_path):
        print(f"⚠️ Cartella immagini non trovata: {images_path}")
        return
    images = create_image_list(images_path)
    photos_by_date = organize_photos_by_date(images)
    photos_by_time = orginize_photos_by_timestamp(photos_by_date)
    responses = [] 
    for i in range(0,5):
        GPTresponse = generate_chatGPT_response(day, photos_by_time)
        response_lines = GPTresponse.split('\n')  #si divide la risposta per linee

        #si rimuovono le parti irrilevanti
        if response_lines[0] == '':
            response_lines.pop(0)
        if response_lines[0] == csv_template.split('\n')[0]:
            response_lines.pop(0)
        if response_lines[len(response_lines)-1] == '':
            response_lines.pop(len(response_lines)-1)
        responses.append(response_lines)


    #si dividono i dati per i timeslot corrispondenti
    responses_data_timeslot_divided = []
    for j in range(len(real_timeframes)):
        response_data = []
        for line in responses:
            response_data.append(line[j])
        responses_data_timeslot_divided.append(response_data)


    #si costruisce il csv finale, considerando i valori ottenuti nelle varie esecuzioni della richiesta, prendendo quello che appare più spesso.
    #per la data e i timeslot, si preferisce un approccio deterministico per ridurre gli errori
    final_csv = csv_template.split('\n')[0] + '\n'
    csv_lines = []
    for i in range(len(real_timeframes)):
        line_csv = str(day) + ' ' + str(real_timeframes[i][0]) + '-' + str(real_timeframes[i][1]) + ' ' #MODIFICARE I TIMEFRAMES CON QUELLI VERI
        bool_crane_used = {'Yes': 0, 'No': 0}
        numbers_of_moves = {}
        weathers = {"Sunny": 0, "Rainy":0, "Stormy":0, "Cloudy":0, "Windy":0}
        
        for timeslot_data in responses_data_timeslot_divided[i]:
            wasCraneUsed = timeslot_data.split(' ')[2]
            numberOfMoves = timeslot_data.split(' ')[3]
            weather = timeslot_data.split(' ')[4]

            if wasCraneUsed in bool_crane_used.keys():
                bool_crane_used[wasCraneUsed] += 1
            
            if numberOfMoves in numbers_of_moves:
                numbers_of_moves[numberOfMoves] +=1
            else:
                numbers_of_moves[numberOfMoves] = 1

            if weather in weathers.keys():
                weathers[weather] += 1


        has_moved = ''  
        for value in bool_crane_used:
            has_moved = str(max(bool_crane_used, key= bool_crane_used.get))
        
        moves = ''
        for value in numbers_of_moves:
            if has_moved == 'Yes':
                moves = str(max(numbers_of_moves, key= numbers_of_moves.get))
            elif has_moved == 'No':
                moves = '0'

        true_weather = ''
        for value in weathers:
            true_weather = str(max(weathers, key= weathers.get))

        line_csv += has_moved + ' ' + moves + ' ' + true_weather + ' \n'
        csv_lines.append(line_csv)
        
    for k in range(len(csv_lines)):
        final_csv += csv_lines[k]

    csv_folder = os.path.join("csv", network)
    os.makedirs(csv_folder, exist_ok=True)
    csv_filename = os.path.join("csv", f"{'image_analysis'}_{str(network)}_{str(camera)}_{str(day)}.csv")

    with open(csv_filename, 'w') as file: 
        file.write(final_csv)
    

"""
if __name__ == "__main__":
    images_path = os.path.join("camera_snapshot", "HOM_BIS", "camera_0")
    image_detection(giornata_lavorativa, images_path, "HOM_BIS", "camera_0")
    image_detection(giornata_lavorativa,images_directory, "HOM_BIS", "camera_0")
"""

