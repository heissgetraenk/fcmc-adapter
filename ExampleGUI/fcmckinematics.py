class FCMCKinematics:
    '''Provide a link between logical geometry axes and actual CAD machine axes'''

    def __init__(self, cad_config):
        #get reference to configuration object
        self.cad_config = cad_config

        #split the config dictionary into more managable parts
        self.transformations = self.cad_config['transformations']
        self.geo_axes = self.cad_config['geoAxes']
        self.mach_axes = self.cad_config['machAxes']


    def _calculateGeoAxValue(self, axis):
        '''calculate geometry axis value from the defined source and correction factor for a given axis'''
        #grab factor and source from configuration object
        src_list = self.transformations[axis]['source']
        factor = float(self.transformations[axis]['factor'])
        source = float(self.mach_axes[src_list[1]][src_list[2]][src_list[3]])

        #calculate geometry axis value
        self.geo_axes[axis]['value'] = factor * source


    def _calculateMachAxValue(self, axis):
        '''calculate machine axis value from the defined source and correction factor for a given axis'''
        #check for manipulations in placement and rotation (sub)somponents
        for component in self.transformations[axis]:
            for sub in self.transformations[axis][component]:
                #grab factor and source from configuration object
                src_list = self.transformations[axis][component][sub]['source']
                factor = float(self.transformations[axis][component][sub]['factor'])
                source = float(self.geo_axes[src_list[1]][src_list[2]])
                
                #calculate the machine axis sub-component axis value (e.g. placement.x)
                self.mach_axes[axis][component][sub] = factor * source
   
    
    def calcAxValues(self, axis_type):
        '''Depending on axis_type: Calculate geo axis values from machine axis values or vice versa'''
        try:
            #iterate through all configured axes
            for axis in self.transformations:
                #differentiate the whether geo or machine axis are to be calculated
                #and check if a axis that was configured in th etransformations is also configured in geoAxes or machAxes
                
                if axis_type == "geoAxes" and axis in self.geo_axes:
                    #calculate the value of a geometry axis
                    self._calculateGeoAxValue(axis)
                
                elif axis_type == "machAxes" and axis in self.mach_axes:
                    #calculate the value of a machine axis
                    self._calculateMachAxValue(axis)

        except:
            pass


    def axis_pos(self, geo_axis):
        '''get a value of a geometry axis from the configured configuration object'''
        return self.cad_config['geoAxes'][geo_axis]['value']


    def axis_list(self):
        '''get a dict of the configured geo axes and a corresponding object name'''
        #extract the configured objects
        geo_dict = self.cad_config['geoAxes']

        #return the keys as a list
        return geo_dict.keys()


    def setGeoAxValue(self, geo, value):
        '''update the value of a given geometry axis in the configuration object'''
        self.cad_config['geoAxes'][geo]['value'] = value