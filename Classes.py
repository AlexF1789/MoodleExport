# ================================= MoodleExport =========================================
# this software is released under the GNU GPL v3.0 license, more info in the LICENSE file
# GitHub repo: https://github.com/AlexF1789/MoodleExport
# ======================================================================================== 

# Classes.py -> this file contains the definition of classes used in the main.py script

import os, json, base64, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint

class Command:
    # class used to store the commands in an OOP style, we could have used a dictionary instead but like this it's more concise and safe in type check
    def __init__(self, name: str, argument: str):
        self.name = name
        self.argument = argument

class Exporter:
    def __init__(self, file_name: str, max_workers: int=2*os.cpu_count()):
        # initialization of the attributes
        self.commands = []
        self.name = None
        self.cookies = None
        self.current_student = 0
        self.chrome_driver = None
        self.max_workers = max_workers

        # file opening to save the commands
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                if line[0] != '#':
                    # it's a command so we can save it in the command list
                    split_line = line.rstrip('\n').split(sep=' ')

                    if len(split_line) < 2:
                        continue

                    # if the command is something we care about we save it in the commands list, otherwise we ignore it
                    if Exporter.__is_command_significative(split_line[0]):
                        self.commands.append(Command(split_line[0], split_line[1]))

    def __is_command_significative(command_name):
        return command_name not in ['save_text']
    
    def execute_commands(self):
        # method used to execute the commands parsed from the configuration file
        current_student = 0
        commands = {
            'supposed': len(self.commands),
            'executed': 0,
            'ignored': 0,
            'file saved': 0,
            'file errors': 0,
            'start': time.ctime(),
            'end': None
        }

        futures = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as thread_pool:
            # for each command we execute it
            for command in self.commands:
                command: Command # type annotation for command

                # we determine which command it is to address it to the opportune method to be executed
                match command.name:
                    
                    # it's the name of the quiz so we start creating the output directory according to it
                    case 'zip-name':
                        self.name = '_'.join(command.argument.split(' '))
                        self.__create_directory()
                        commands['executed'] += 1

                    # it's the session cookie so we save it for the requests
                    case 'cookies':
                        self.cookies = dict()
                        cookies = str(base64.b64decode(command.argument)).lstrip("b'").rstrip("'").split('; ')
                        for cookie in cookies:
                            cookie = cookie.split('=')
                            if cookie[0] == 'MoodleSession':
                                self.cookies['MoodleSession'] = cookie[1]
                                break
                        commands['executed'] += 1

                    # it's a link so we save the regarding pdf
                    case 'save-pdf':
                        if self.cookies is None or self.name is None:
                            raise Exception('File not formatted correctly! Quiz name and/or session cookie missing')
                        
                        # in case we didn't setup the chrome driver we proceed
                        if self.chrome_driver is None:
                            self.__setup_chrome(command.argument)
                        
                        # we append the __save_pdf method call to the thread pool incrementing the current student number for the pdf file name
                        current_student += 1
                        futures.append(thread_pool.submit(self.__save_pdf, command.argument, current_student))

                        commands['executed'] += 1

                    case _:
                        commands['ignored'] += 1

        # here we launche the threads to obtain the stats
        for future in futures:
            if future.result():
                commands['file saved'] += 1
            else:
                commands['file errors'] += 1

        self.chrome_driver.quit()

        # here we save the end of commands execution stats
        commands['end'] = time.ctime()

        # stats print for debug
        print('commands executed with the following stats:')
        pprint(commands)

        # stats.json file creation
        try:
            with open('stats.json', 'w', encoding='utf-8') as output_file:
                output_file.write(json.dumps({
                    'name': self.name,
                    'stats': commands
                }))
            print('stats have been exported to stats.json file')
        except Exception:
            print('there was an error saving the stats')
        

    def __create_directory(self):
        # method to create the directory where the reports will be saved (output/<zip-name>)
        directory = os.path.join('output', self.name)
        os.makedirs(directory, exist_ok=True)

    def __setup_chrome(self, link: str):
            # from a casual link we're filtering the address to configure the selenium instance
            secure = link[4] == 's'
            address = link[(8 if secure else 7):].split('/')[0]

            if ':' in address:
                address, port = address.split(':')
            else:
                port = 443 if secure else 80

            complete_address = ('https://' if secure else 'http://') + address + ':' + port

            # we configure chrome options and create the driver passing them as a parameter
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')

            self.chrome_driver = webdriver.Chrome(options=chrome_options)

            # we add the MoodleSession cookie
            if 'MoodleSession' not in self.cookies:
                raise Exception('missing Moodle cookie!')
            
            # to add the cookie we must visit the domain at least once, after having done so we add the cookie
            self.chrome_driver.get(complete_address)

            self.chrome_driver.add_cookie({
                'name': 'MoodleSession',
                'value': self.cookies['MoodleSession'],
                'domain': address
            })

            # here we define the print options which will be used later while saving the PDFs
            self.print_options = {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True,
                'preferCSSPageSize': True,
                'paperWidth': 8.27,
                'paperHeight': 11.69
            }

    def __save_pdf(self, link: str, current_attempt: int) -> bool:
        # method used to save a certain URL to a PDF document, it works only if the chrome_driver has been initialized
        try:
            self.chrome_driver.get(link)
            print(f'Exporting the {current_attempt} attempt...')
            pdf = self.chrome_driver.execute_cdp_cmd('Page.printToPDF', self.print_options)
            with open(os.path.join('output', self.name, f'{current_attempt}.pdf'), 'wb') as output_file:
                output_file.write(base64.b64decode(str(pdf)))
            return True
        except:
            print(f'Error exporting the {current_attempt} attempt...')
            return False