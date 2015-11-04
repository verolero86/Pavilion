#!python


#  ###################################################################
#
#  Disclaimer and Notice of Copyright 
#  ==================================
#
#  Copyright (c) 2015, Los Alamos National Security, LLC
#  All rights reserved.
#
#  Copyright 2015. Los Alamos National Security, LLC. 
#  This software was produced under U.S. Government contract 
#  DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL), 
#  which is operated by Los Alamos National Security, LLC for 
#  the U.S. Department of Energy. The U.S. Government has rights 
#  to use, reproduce, and distribute this software.  NEITHER 
#  THE GOVERNMENT NOR LOS ALAMOS NATIONAL SECURITY, LLC MAKES 
#  ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY 
#  FOR THE USE OF THIS SOFTWARE.  If software is modified to 
#  produce derivative works, such modified software should be 
#  clearly marked, so as not to confuse it with the version 
#  available from LANL.
#
#  Additionally, redistribution and use in source and binary 
#  forms, with or without modification, are permitted provided 
#  that the following conditions are met:
#  -  Redistributions of source code must retain the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer. 
#  -  Redistributions in binary form must reproduce the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer in the documentation 
#     and/or other materials provided with the distribution. 
#  -  Neither the name of Los Alamos National Security, LLC, 
#     Los Alamos National Laboratory, LANL, the U.S. Government, 
#     nor the names of its contributors may be used to endorse 
#     or promote products derived from this software without 
#     specific prior written permission.
#   
#  THIS SOFTWARE IS PROVIDED BY LOS ALAMOS NATIONAL SECURITY, LLC 
#  AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
#  IN NO EVENT SHALL LOS ALAMOS NATIONAL SECURITY, LLC OR CONTRIBUTORS 
#  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, 
#  OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
#  OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
#  OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
#  OF SUCH DAMAGE.
#
#  ###################################################################


"""  Implementation of PBS Job Controller  """

import sys
import os
import subprocess
import re
from basejobcontroller import JobController
from helperutilities import which


class PbsJobController(JobController):
    """ class to run a job using PBS """

    @staticmethod
    def is_pbs_system():
        if which("qstat"):
            return True
        else:
            return False

    # .. some setup and let the qsub command fly ...
    def start(self):

        # Stuff any buffered output into the output file now
        # so that the the order doesn't look all mucked up
        sys.stdout.flush()

        qsub_cmd = "qsub -V "

        # handle optionally specified queue
        if self.configs['pbs']['queue']:
            qsub_cmd += "-q " + self.configs['pbs']['queue'] + " "

        # add test name
        qsub_cmd += "-N " + self.name + " "

        # add account name
        if self.configs['pbs']['account']:
            qsub_cmd += "-A " + self.configs['pbs']['account'] + " "

        # get time limit, if specified
        time_lim = ''
        try:
            time_lim = str(self.configs['pbs']['time_limit'])
            self.logger.info(self.lh + " : time limit = " + time_lim)
        except TypeError:
            self.logger.info(self.lh + " Error: time limit value, test suite entry may need quotes")

        node_list = ''
        try:
            node_list = self.configs['pbs']['node_list']
            self.logger.info(self.lh + " : node list = " + node_list)
        except:
            self.logger.info(self.lh + " Error: node list value incorrect")

        # variation passed as arg0 - nodes, arg1 - ppn
        nnodes = str(self.configs['pbs']['num_nodes'])
        #nnodes = str(self.job_variation[0])
        #ppn = str(self.job_variation[1])
        ppn = str(self.configs['pbs']['procs_per_node'])

        self.logger.info(self.lh + " : nnodes=" + nnodes)
        self.logger.info(self.lh + " : ppn=" + ppn)
        self.logger.info(self.lh + " : args=" + str(self.configs['run']['test_args']))

        pes = int(ppn) * int(nnodes)
        self.logger.info(self.lh + " : npes=" + str(pes))

        # ++ PV_PESPERNODE : Number of cores per node
        os.environ['GZ_PESPERNODE'] = ppn
        os.environ['PV_PESPERNODE'] = ppn

        # ++ PV_NNODES : Number of nodes allocated for this job
        os.environ['GZ_NNODES'] = nnodes
        os.environ['PV_NNODES'] = nnodes
        print "<nnodes> " + nnodes

        # ++ PV_NPES : Number of pe's allocated for this job
        os.environ['PV_NPES'] = str(pes)
        os.environ['GZ_NPES'] = os.environ['PV_NPES']
        print "<npes> " + str(pes)

        # create working space here so that each msub run gets its own
        #self.setup_working_space()

        # print the common log settings here right after the job is started
        self.save_common_settings()

        # store some info into ENV variables that jobs may need to use later on.
        self.setup_job_info()

        # setup unique PBS stdout and stderr path names
        # ++ PV_JOB_RESULTS_LOG_DIR : Path where results for this job are placed
        se = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stderr"
        so = os.environ['PV_JOB_RESULTS_LOG_DIR'] + "/drm.stdout"
        qsub_cmd += "-o " + so + " -e " + se + " "

        if node_list:
            qsub_cmd += "-l nodes=" + node_list
        else:
            qsub_cmd += "-l nodes=" + nnodes
        if time_lim:
            qsub_cmd += ",walltime=" + time_lim

        # ++ PV_RUNHOME : Path where this job is run from
        run_cmd = os.environ['PV_RUNHOME'] + "/" + self.configs['run']['cmd']
        os.environ['USER_CMD'] = run_cmd

        qsub_cmd += " " + os.environ['PVINSTALL'] + "/PAV/modules/pbs_job_handler.py"

        if PbsJobController.is_pbs_system():
            self.logger.info(self.lh + " : " + qsub_cmd)
            # call to invoke real PBS command
            self.logger.info(": <MINE:is_pbs_system> qsub command: " + str(qsub_cmd))
            self.logger.info(": <MINE:is_pbs_system> run command: " + str(run_cmd))
            output = subprocess.check_output(qsub_cmd, shell=True)
            self.logger.info(": <MINE:is_pbs_system> output qsub: " + str(output))

            # Finds the jobid in the output from qsub. 
            match = re.search("^(\d+))[\r]?$",  output, re.IGNORECASE | re.MULTILINE)
            jid = 0
            if match.group(1):
                jid = match.group(1)

            self.logger.info(": <JobID> " + str(jid))

        else:
            # fake-out section to run on basic unix system
            fake_job_cmd = os.environ['PVINSTALL'] + "/PAV/modules/pbs_job_handler.py"
            print "<MINE> qsub command: " + str(qsub_cmd)
            print "<MINE> command: " + str(cmd)
            p = subprocess.Popen(fake_job_cmd, stdout=self.job_log_file, stderr=self.job_log_file, shell=True)
            # wait for the subprocess to finish
            (output, errors) = p.communicate()
            if p.returncode or errors:
                print "Error: something went wrong!"
                print [p.returncode, errors, output]
                self.logger.info(self.lh + " run error: " + errors)
        

    
# this gets called if it's run as a script/program
if __name__ == '__main__':
    sys.exit()
