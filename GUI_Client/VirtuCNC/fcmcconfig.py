import json

class FCMCConfig:
    '''Helper class to handle the json settings file containing the info on the configuration of the CAD model'''

    def __init__(self, path):

        self.config = {}

        #open file from given path
        with open(path) as settings:
            #extract content
            content = settings.read()

            #convert it from json to py dict
            self.config = json.loads(content)


    def get_config(self):
        '''getter for passing file info to calling process'''
        return self.config
        