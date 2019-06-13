from json import load
import re
from datetime import datetime
from shutil import make_archive, move
from os import path, pardir, listdir
from numpy import size


class BuildProg:
    """

    """
    def __init__(self, crpath='../crBasic/', f_config='../met.config'):
        """

        :return:
        """
        self.crBasic = []
        self.prog_vers = "0.0"
        self.met_config = {}

        self._read_crBasic(crpath)
        self._read_met_config(f_config)

        self.comp_ordered = ['snow', 'twr', 'shlt', 'PAR', 'pyranometer', 'net radiometer', 'sonic', 'SA', 'PWR']

    def _read_crBasic(self, f_path):
        '''
        Read in all .CR# files. Each row is read in as a single string and all rows are concatenated into a list.
         Each files is read into a dictionary using the file name as dictionary keys.

        ..Example::
            SA_pulic.cr1 and SA_tbl.cr1

            are read into

            {puclic:{SA:[]}, tbl:{SA:[]}}
        :param f_path: a directory name
        :return: dictionary is assigned to class object
        '''
        f_names = listdir(f_path)
        files = {}

        for cr in f_names:
            f = open(f_path + cr, 'r')
            filetext = f.read()
            f.close()
            files[cr] = filetext

        programs = {'public': {'SYS': {}},
                    'tbl': {'SYS': {}, '105': {}},
                    'header': {},
                    'prog': {},
                    'footer': {}}

        for k, v in files.iteritems():
            keys = k.split('.')[0].split('_')
            val = v.split('\n')
            if size(keys) is 2:
                programs[keys[1]].update({keys[0]: val})
            elif size(keys) is 3:
                if keys[2] == 'SYS':
                    decl = self.get_SYS_declarations(v)
                    out = self.get_SYS_tbl_cols(v)
                    programs['public']['SYS'].update({keys[0]: decl})
                    programs['tbl']['SYS'].update({keys[0]: out})
                else:
                    programs[keys[1]][keys[2]].update({keys[0]: val})

        self.crBasic = programs

    def _read_met_config(self, file_n='./met.config'):
        """
        Read JSON file met.config. This file contains basic information about each logger, it's sensors, and it's wiring.
        :param file_n: string containing filename or path
        :return: dictionary assigned to class object
        """

        lid_list = load(open(file_n))
        lid_adj = self._convert_keys_to_float(lid_list)

        self.met_config = lid_adj

    def _convert_keys_to_float(self, dict_name):
        """
        Converts dictionary primary (or first level) keys from string to float
        :param dict_name: dictionary
        :return: dictionary
        """
        new_dict = {}
        for k, v in dict_name.iteritems():
            new_dict[int(k)] = v

        return new_dict

    def _find_SYS_split(self, prog_str):
        """
        Index the split between variable declarations and table outputs from a CRBasic program for SYS.

        For derived measurements or measurements with multiple factors, intermediate variables are output to a SYS or
        system table. This usually requires the declaration of the intermediate variable, as well as the output of that
        variable into the SYS table. This function indexes the split between declarations and table outputs.

        ..Example::
            pyranometer_tbl_SYS.cr1

            Dim SOLAR_Wm2_RAW
            '------------/\Declare_Variable/\---------\/Table_Output\/--------------------
                Minimum(1, SOLAR_Wm2_RAW,FP2,False,0)

            _find_SYS_split returns: (18,96)


        :param prog_str:
        :return:
        """
        r = re.search("'-----[^\n]*/\\-*\\/*", prog_str)

        if r is not None:
            return r.span()
        else:
            return (0, 0)

    def get_SYS_declarations(self, prog_str):
        """
        Extract declarations of intermediate variables from a CRBasic file.

        For derived measurements or measurements with multiple factors, intermediate variables are output to a SYS or
        system table. This usually requires the declaration of the intermediate variable, as well as the output of that
        variable into the SYS table. This function extracts the declaration of intermediate variables.

        ..Example::
            pyranometer_tbl_SYS.cr1

            Dim SOLAR_Wm2_RAW
            '------------/\Declare_Variable/\---------\/Table_Output\/--------------------
                Minimum(1, SOLAR_Wm2_RAW,FP2,False,0)

            get_SYS_declarations returns: 'Dim SOLAR_Wm2_RAW'

        :param prog_str:
        :return:
        """
        i, _ = self._find_SYS_split(prog_str)
        decl = prog_str[:i].split('\n')

        return decl

    def get_SYS_tbl_cols(self, prog_str):
        """
        Extract calls for variables to output to a table from a CRBasic file.

        For derived measurements or measurements with multiple factors, intermediate variables are output to a SYS or
        system table. This usually requires the declaration of the intermediate variable, as well as the output of that
        variable into the SYS table. This function extracts the program call to write variables to the SYS table.

        ..Example::
            pyranometer_tbl_SYS.cr1

            Dim SOLAR_Wm2_RAW
            '------------/\Declare_Variable/\---------\/Table_Output\/--------------------
                Minimum(1, SOLAR_Wm2_RAW,FP2,False,0)

            get_SYS_tbl_cols returns: '     Minimum(1, SOLAR_Wm2_RAW,FP2,False,0)'

        :param prog_str:
        :return:
        """
        _, i = self._find_SYS_split(prog_str)
        i += 1
        tbl = prog_str[i:].split('\n')

        return tbl

    def get_prog_file_name(self, lid):
        """

        :param rs_num:
        :return:
        """
        site = self.met_config[lid]['Site']
        model = self.met_config[lid]['model']

        vers = self.prog_vers
        vers = '0'+vers if vers.split('.')[0].__len__() < 2 else vers

        # pick file extension .cr1 for CR1000, .cr3 for CR3000
        if model == "1000":
            f_ext = ".cr1"
        elif model == "3000":
            f_ext = ".cr3"
        else:
            raise Warning('%s %s has an unknown logger model with no matching file extension'%(site, str(lid)))

        return site + '_' + str(lid) + "_v" + vers + f_ext

    def get_crd_file_prefix(self, lid):
        """

        :param rs_num:
        :return:
        """
        site = self.met_config[lid]['Site']

        return site + '_' + str(lid) + '_'

    def get_header(self, fname):
        """

        :param fname:
        :return:
        """
        header = ["' Program name: " + fname,
                  "' Auto generated by cr_assemble.py on " + datetime.now().strftime('%m-%d-%y %H:%M')]

        return header

    def save_prog(self, txt, fname=None, dir_n='./bin/'):
        """

        :param txt:
        :param fname:
        :param dir_n:
        :return:
        """
        if fname is None:
            fname = self.get_prog_file_name()

        with open(dir_n + fname, 'w+') as f:
            f.write(txt)

    def get_sensor_parameters(self, sens_param):
        '''
        cycles through logger sensors and returns strings declaring variables and values
        :param sens_param: dictionary of different sensors
        :return: returns list of sensors.
        '''

        sensors = []
        toSYStbl = []
        for s, p in sens_param.iteritems():
            if 'offset' in p:
                sensors.append('Public offset_' + s + ' = ' + str(p['offset']))
                sensors.append('Public coef_' + s + ' = ' + str(p['coef']))

                toSYStbl.append('  Sample(1,offset_' + s + ',FP2)')
                toSYStbl.append('  Sample(1,coef_' + s + ',FP2)')

            if 'DiffChan' in p:
                sensors.append('Const diff_' + s + ' = ' + str(p['DiffChan'].keys()[0]))
            elif 'SE' in p:
                sensors.append('Const se_' + s + ' = ' + str(p['SE'].keys()[0]))
            elif 'Com' in p:
                sensors.append('Const com_' + s + ' = ' + str(p['Com'].keys()[0]))
            elif 'PChan' in p:
                sensors.append('Const pchan_' + s + ' = ' + str(p['PChan'].keys()[0]))

            if 'Vx' in p:
                sensors.append('Const vx_' + s + ' = ' + p['Vx'].keys()[0])

        sensors.append('\n')

        return sensors, toSYStbl

    def _SYScomp_loop(self, comp, cr_sys):

        sys = []
        for c in comp:
            if c.upper() == 'SA' or not cr_sys.has_key(c):
                continue
            sys.extend(cr_sys[c])

        return sys

    def _format_sys_tbl(self, lid):

        cr = self.crBasic
        sensors = self.met_config[lid]['measure']
        comp = self.met_config[lid]['components']
        cr_sys_t = cr['tbl']['SYS']
        tbl_sys = []

        # call/initiate SYS table
        tbl_sys.extend(cr_sys_t['met'])

        # for each component other than SA, look for values that are stored in the SYS table
        tbl_comp = self._SYScomp_loop(comp, cr_sys_t)
        tbl_sys.extend(tbl_comp)

        # place each of the sensor coefficients and offsets into the SYS table
        _, sensor_tbl = self.get_sensor_parameters(sensors)
        tbl_sys.extend(sensor_tbl)

        # end the table
        tbl_sys.append('EndTable\n')

        return tbl_sys

    def _format_sys_decl(self, lid):

        cr = self.crBasic
        comp = self.met_config[lid]['components']
        sensors = self.met_config[lid]['measure']
        cr_sys_p = cr['public']['SYS']

        sys_param = []

        # system diagnostics header
        sys_param.extend(["'SYSTEM Diagnostics",
                          "'#######################################################",
                          "'SYS Table variables"])

        # for each component other than SA, look for values that are declared
        decl_comp = self._SYScomp_loop(comp, cr_sys_p)
        sys_param.extend(decl_comp)

        # Add public variables controlling wiring and ports
        # coefficients, offsets, Vx, SE, COM, Diff numbers
        sensor_decl, _ = self.get_sensor_parameters(sensors)
        sys_param.extend(sensor_decl)

        return sys_param

    def format_sys(self, lid):
        """

        :param lid:
        :return:
        """
        # System parameters include both declaration of special variables, and a table output that changes depending on
        # which sensors and components are present
        sys = self._format_sys_decl(lid) + self._format_sys_tbl(lid)

        '''
        cr = self.crBasic
        comp = self.met_config[lid]['components']
        sensors = self.met_config[lid]['measure']
        cr_sys_t = cr['tbl']['SYS']
        cr_sys_p = cr['public']['SYS']

        sys_param = []
        tbl_sys = []

        # power table, followed by system diagnostics header
        sys_param.extend(cr['tbl']['PWR'])
        sys_param.extend(["'SYSTEM Diagnostics",
                          "'#######################################################",
                          "'SYS Table variables"])

        # start SYS with table call
        tbl_sys.extend(cr_sys_t['met'])

        for c in comp:
            if c.upper() == 'SA' or not cr_sys_t.has_key(c):
                continue
            # Declare system variables and add them to a SYS table that tracks logger and sensor function
            # SA is excluded, because it's function is recorded in the CONTrol table
            sys_param.extend(cr_sys_p[c])
            tbl_sys.extend(cr_sys_t[c])

        sensor_decl, sensor_tbl = self.get_sensor_parameters(sensors)

        tbl_sys.extend(sensor_tbl)
        tbl_sys.append('EndTable\n')

        # Add public variables controlling wiring and ports
        # coefficients, offsets, Vx, SE, COM, Diff numbers
        sys_param.extend(sensor_decl)
        '''

        return sys

    def format_tbl_105(self, lid):
        """

        :param lid:
        :return:
        """
        cr = self.crBasic
        comp = self.met_config[lid]['components']
        tbl_105 = []

        # start 105 tables with table call
        tbl_105.extend(cr['tbl']['105']['met'])

        for c in comp:
            # Assemble Table105 and sensor measurements from list of sensor groups on this logger
            tbl_105.extend(cr['tbl']['105'][c])

        # end tables
        tbl_105.append('EndTable\n')

        return tbl_105

    def format_pblc_var(self, lid):
        """

        :param lid:
        :return:
        """
        cr = self.crBasic
        comp = self.met_config[lid]['components']
        # This is a list of station components in a specific order
        ordered = self.comp_ordered
        # initiate empty variables
        pblc = []

        # program header, comments, and universal Pulic variables: e.g. LID, BatteryVoltage
        pblc.extend(cr['header'].values()[0])

        # loop through components. Use a list with a preset order instead of looping through comp list, .
        for c in ordered:
            if comp.count(c):
                # Declare program variables, aliases, and assign units to variables from each sensor group on logger
                pblc.extend(cr['public'][c])

        return pblc

    def insert_check_reset(self, textstr, comp):
        """

        :param textstr:
        :param comp:
        :return:
        """

        check = {'SA': '      PUMPVOLTS_CHECK = NAN\n',
                 'snow': '      SNOWDEPTH_CHECK = NAN\n      SWE_CHECK = NAN\n'}

        match = re.search('If.*\s*[^Public]BATTERY_V_CHECK.*=.*NAN\n', textstr, flags=(re.IGNORECASE))
        i = match.end()
        for c in check:
            if c in comp:
                textstr = textstr[:i] + check[c] + textstr[i:]
                i += check[c].__len__()

        return textstr

    def format_prog(self, lid):
        """

        :param lid:
        :return:
        """
        cr = self.crBasic
        comp = self.met_config[lid]['components']
        # This is a list of station components in a specific order
        ordered = self.comp_ordered

        # place main program header
        prog = ["'\\\\\\\\\\\\\\\\\\\\\\\\\\\ MAIN PROGRAM ////////////////////////////\nBeginProg\n"]
        prog.extend(cr['prog']['met'])

        # loop through components. Use a list with a preset order instead of looping through comp list, .
        for c in ordered:
            if comp.count(c):
                # write program calls
                prog.extend(cr['prog'][c])

        # Add power controls program
        prog.extend(cr['prog']['PWR'])

        # If stand alone rain gauge, add a control table output
        if comp.count('SA'):
            prog.extend(["\n    '////5 minute Control Table output for SA////", "    CallTable CONT\n"])

        # end program
        prog.extend(cr['footer']['met'])

        # Insert sonic fast scan before rest of program
        if comp.count('sonic'):
            # The sonic requires a fast scan, which must precede the slow scan
            prog[:0] = cr['prog']['sonic']

        return prog

    def build_met_prog(self, lid, fpath='../bin/'):
        """

        :param lid:
        :return:
        """

        cr = self.crBasic
        comp = self.met_config[lid]['components']
        sensors = self.met_config[lid]['measure']
        vers = self.prog_vers

        fname = self.get_prog_file_name(lid)
        header = self.get_header(fname)

        # Assemble file: declare variables, table output, and write program
        if comp.count('SA'):
            sa = cr['tbl']['SA']
        else:
            sa = []

        #######################
        cr_file = header + self.format_pblc_var(lid) + sa + cr['tbl']['PWR'] + self.format_sys(lid) + \
                  self.format_tbl_105(lid) + self.format_prog(lid)
        #######################
        # convert list to string
        cr_text = "\n".join(cr_file)
        # insert check values
        cr_text = self.insert_check_reset(cr_text, comp)

        # fill in site specific values
        # !!-----------------------------!!
        # logger ID
        cr_text = re.sub('^[CONST|PUBLIC|DIM].*LID.*', 'Const LID                = ' + str(lid), cr_text,
                         flags=re.MULTILINE)

        # crd file name
        crd = self.get_crd_file_prefix(lid)
        cr_text = re.sub('CRD:+\s*(?=\S)', 'CRD:' + crd, cr_text, flags=(re.MULTILINE&re.IGNORECASE))

        # snow sensor distance above ground
        if comp.count('snow'):
            distance = sensors['SNOW_RAW_DIST']['SNOW_INITIAL_DISTANCE']
            snow_str = 'Public SNOW_INITIAL_DISTANCE = ' + str(distance)
            cr_text = re.sub('(^[Public|Dim|Const]+.*SNOW_INITIAL_DISTANCE+.*)', snow_str, cr_text,
                             flags=re.MULTILINE)

        # program version
        cr_text = re.sub('(^[Public|Dim|Const]+.*PROG_VERS+.*$)', 'Public PROG_VERS       = ' + str(vers), cr_text,
                         flags=re.MULTILINE)
        '''
        # A simple string replace is faster, but is more prone to errors (case, sensitive exact matches only)
        # and a list is unbearably slow. Even adding the time of converting list to string regex is faster
        %%timeit
        crf = cr_file
        for c in crf:
            if 'LID' in c:
                edit = c.replace('=', '= 234')
                i = crf.index(c)
                crf.remove(c)
                crf.insert(i, edit)
        
        100 loops, best of 3: 6.64 ms per loop  
        
        %%timeit  
        cr_text = '/n'.join(cr_file)
        
        10000 loops, best of 3: 54.6 us per loop
        
        %%timeit 
        re.sub('^[CONST|PUBLIC|DIM].*LID.*$','Const LID = 234', cr_text, re.MULTILINE)
        
        10000 loops, best of 3: 104 us per loop
        
        %%timeit
         cr_text.replace('LID =', 'LID = 234')

        100000 loops, best of 3: 7.46 us per loop
        '''

        self.save_prog(cr_text, fname, dir_n=fpath)
        print 'Successful write to ' + fpath + fname + '\n'

    def build_all_prog(self, fpath='../bin/'):
        """

        :return:
        """
        lid_list = self.met_config

        for lid in lid_list.iterkeys():
            self.build_met_prog(lid, fpath)

        print '-------------------------------------\nAll stations sucessfully written to %s'%fpath

    def zip_all_prog(self, outpath='/bin/'):
        """

        :return:
        """
        fpath = path.abspath(pardir)
        name = fpath + '/MET_v' + str(self.prog_vers)
        make_archive(name, 'zip', fpath, 'bin')
        move(name + '.zip', fpath + outpath)

if __name__ == "__main__":
    programs = BuildProg()
    #t = programs.build_met_prog(234)
    # programs
    # with open('../bin/modules_TestCent.cr1', 'w') as f:
    #     f.write(t)#"\n".join(t))
    programs.build_all_prog()
    programs.zip_all_prog()
