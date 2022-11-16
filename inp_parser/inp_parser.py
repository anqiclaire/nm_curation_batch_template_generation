class Section():
    def __init__(self, row):
        self.name = ''
        self.attr = {}
        self.value = {'raw':[]}
        self.nrows = 0
        self.parse_header(row)

    def parse_header(self, header_row):
        header_segs = header_row.split(',')
        self.name = header_segs[0].strip()
        for i in range(1,len(header_segs)):
            seg = header_segs[i].upper() # use upper case
            if '=' in seg:
                attr,val = seg.split('=')
                if attr.strip() in self.attr:
                    print(f'Warning: {attr.strip()} appears\
more than once for {self.name}')
                self.attr[attr.strip()] = val.strip()
            else:
                if seg.strip() in self.attr:
                    print(f'Warning: {seg.strip()} appears\
more than once for {self.name}')
                self.attr[seg.strip()] = True
        return

    def view(self):
        print('='*20)
        print(f'Name: {self.name}')
        print(f'Attributes:')
        for k,v in self.attr.items():
            print(f'  {k} = {v}')
        print(f'# of rows: {self.nrows}')
        print(f'value: {self.value.keys()}')

    def update(self, row):
        self.value['raw'].append(row)
        self.nrows += 1

    def __len__(self):
        return 1 if self.name else 0

    def to_dict(self):
        '''
        Convert the object to a dict with curatable information.
        Use the name in the Excel template as key.
        Value should be a list with positional mapping [col B, col C, col D]
        '''
        return {}

class Element(Section):
    # overwrite the to_dict method
    def to_dict(self):
        template = {}
        # save number of elements
        template['Number of Elements'] = ['inserted by inp_parser', self.nrows]
        # save element type
        if 'TYPE' in self.attr:
            template['Element Type - Abaqus'] = ['inserted by inp_parser',
                                                 self.attr['TYPE']]
        return template

class SteadyStateDynamics(Section):
    # overwrite the update method
    def update(self, row):
        self.nrows += 1
        segs = row.split(',')
        self.value['fmin'] = float(segs[0])
        self.value['fmax'] = float(segs[1])
        self.value['num_freq'] = int(segs[2])
    # overwrite the to_dict method
    def to_dict(self):
        # the presence of this object infers
        # "Steady state dynamic" for "Loading Type"
        template = {'Loading Type': ['', 'Steady state dynamic']}
        if 'fmin' in self.value:
            template['Min frequency'] = ['inserted by inp_parser',
                                         self.value['fmin']]
        if 'fmax' in self.value:
            template['Max frequency'] = ['inserted by inp_parser', 
                                         self.value['fmax']]
        if 'num_freq' in self.value:
            template['Number of Frequency Intervals'] = ['', 
                                                         self.value['num_freq']]
        return template

class Elastic(Section):
    def __init__(self, row):
        super().__init__(row)
        # by default
        if 'MODULI' not in self.attr:
            self.attr['MODULI'] = 'LONG TERM'
    # overwrite the update method
    def update(self, row):
        self.nrows += 1
        segs = row.split(',')
        self.value['youngs_modulus'] = float(segs[0])
        self.value['poissons_ratio'] = float(segs[1])

class Density(Section):
    # overwrite the update method
    def update(self, row):
        self.value['density'] = float(row)
        self.nrows += 1

class Viscoelastic(Section):
    # overwrite the update method
    def update(self, row):
        self.nrows += 1
        segs = row.split(',')
        self.value['wg*_real'] = self.value.get('wg*_real',[])
        self.value['wg*_real'].append(float(segs[0]))
        self.value['wg*_imag'] = self.value.get('wg*_imag',[])
        self.value['wg*_imag'].append(float(segs[1]))
        self.value['wk*_real'] = self.value.get('wk*_real',[])
        self.value['wk*_real'].append(float(segs[2]))
        self.value['wk*_imag'] = self.value.get('wk*_imag',[])
        self.value['wk*_imag'].append(float(segs[3]))
        self.value['frequency'] = self.value.get('frequency',[])
        self.value['frequency'].append(float(segs[4]))

class Boundary(Section):
    def __init__(self, row):
        super().__init__(row)
        # mapping between abaqus BC keywords and CAE BC categories described in:
        # http://194.167.201.93/English/SIMACAEPRCRefMap/simaprc-c-boundary.htm
        self.refmap = {
        'DISPLACEMENT': 'Displacement/Rotation',
        'VELOCITY': 'Velocity/Angular velocity',
        'ACCELERATION': 'Acceleration/Angular acceleration',
        }
        # by default
        if 'TYPE' not in self.attr:
            self.attr['TYPE'] = 'DISPLACEMENT'
    # overwrite the update method
    def update(self, row):
        self.nrows += 1
        segs = row.split(',')
        # node could be node number (int) or set name (str)
        self.value['node'] = int(segs[0]) if segs[0].strip().isdigit() else segs[0].strip()
        self.value['first_dof'] = int(segs[1])
        self.value['last_dof'] = int(segs[2])
        self.value['magnitude'] = float(segs[3])
    # overwrite the to_dict method
    def to_dict(self):
        template = {}
        sign = '+' # keep magnitude positve, put as prefix of x,y,z direction
        template['Boundary Condition Type'] = [self.refmap[self.attr['TYPE']]]
        # disable Magnitude and Direction for now
        # if 'magnitude' in self.value:
        #     if self.value['magnitude'] < 0:
        #         sign = '-' # update sign
        #     template['Magnitude'] = ['inserted by inp_parser',
        #                              abs(self.value['magnitude'])]
        # if 'first_dof' in self.value and 'last_dof' in self.value:
        #     directions = ['x','y','z','end']
        #     template['Direction'] = template.get('Direction',[])
        #     for i in range(self.value['first_dof'],self.value['last_dof']+1):
        #     # self.value['first_dof'] == 1 maps to 'x', 2 maps to 'y'
        #     # 'x', 'y', 'z', accessed by directions[i-1]
        #         template['Direction'].append(sign + directions[i-1])
        return template
    
class Parser():
    # by default skip *Equation
    def __init__(self, inp_file, skip={'*Equation'}):
        if not inp_file.lower().endswith('.inp'):
            inp_file += '.inp'
        self.skip = skip
        self.sections = []
        self.comments = []
        self.parse(inp_file)

    def parse(self, inp_file):
        self.prev_section = Section('')
        with open(inp_file, 'r') as f:
            for row in f:
                # comment rows
                if row.startswith('**'):
                    self.comments.append(row)
                # header rows
                elif row.startswith('*'):
                    if self.prev_section and\
                    self.prev_section.name not in self.skip:
                        # save prev_section
                        self.sections.append(self.prev_section)
                    # update prev_section with current row
                    if row.lower().startswith('*steady state dynamics'):
                        self.prev_section = SteadyStateDynamics(row)
                    elif row.lower().startswith('*elastic'):
                        self.prev_section = Elastic(row)
                    elif row.lower().startswith('*density'):
                        self.prev_section = Density(row)
                    elif row.lower().startswith('*boundary'):
                        self.prev_section = Boundary(row)
                    elif row.lower().startswith('*viscoelastic'):
                        self.prev_section = Viscoelastic(row)
                    elif row.lower().startswith('*element') and \
                    not row.lower().startswith('*element output'):
                        self.prev_section = Element(row)
                    else:
                        self.prev_section = Section(row)
                # value rows
                else:
                    self.prev_section.update(row)
        return

    def view(self):
        for comment in self.comments:
            print('='*20)
            print(f'Comment: {comment}')
        for sec in self.sections:
            sec.view()

    def to_dict(self):
        '''
        Generate the dict that contains all information that goes into the Excel
        '''
        template = {'Software Used': ['Abaqus']}
        # update the dict, assume no duplicated keys exist
        print('Warning: duplicated keys will be overwritten!')
        for sec in self.sections:
            template.update(sec.to_dict())
        return template

    def __getitem__(self, index):
        return self.sections[index]

if __name__ == '__main__':
    parser = Parser('20_10_500_0_0.0_0.15_1_58.inp', skip={'*Equation','*Nset'})
    parser.view()