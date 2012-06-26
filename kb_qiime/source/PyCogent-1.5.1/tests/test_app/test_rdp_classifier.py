#!/usr/bin/env python
"""Tests for the rdp_classifier_2.0.1 application controller"""

import os
from cStringIO import StringIO
from os import getcwd, environ, remove, listdir
from shutil import rmtree

import tempfile
from cogent.app.util import ApplicationNotFoundError, ApplicationError,\
    get_tmp_filename
from cogent.app.rdp_classifier import (
    RdpClassifier, RdpTrainer, assign_taxonomy, train_rdp_classifier,
    train_rdp_classifier_and_assign_taxonomy, parse_rdp_assignment
    )
from cogent.util.unit_test import TestCase, main

__author__ = "Kyle Bittinger"
__copyright__ = "Copyright 2007-2011, The Cogent Project"
__credits__ = ["Kyle Bittinger"]
__license__ = "GPL"
__version__ = "1.5.1"
__maintainer__ = "Kyle Bittinger"
__email__ = "kylebittinger@gmail.com"
__status__ = "Prototype"

class RdpClassifierTests(TestCase):
    def setUp(self):
        # fetch user's RDP_JAR_PATH
        if 'RDP_JAR_PATH' in environ:
            self.user_rdp_jar_path = environ['RDP_JAR_PATH']
        else:
            self.user_rdp_jar_path = 'rdp_classifier-2.2.jar'
        self.output_file = tempfile.NamedTemporaryFile()

    def test_default_java_vm_parameters(self):
        """RdpClassifier should store default arguments to Java VM."""
        a = RdpClassifier()
        self.assertContains(a.Parameters, '-Xmx')
        self.assertEqual(a.Parameters['-Xmx'].Value, '1000m')

    def test_parameters_list(self):
        a = RdpClassifier()
        parameters = a.Parameters.keys()
        parameters.sort()
        self.assertEqual(parameters, ['-Xmx', '-f', '-o', '-t'])

    def test_assign_jvm_parameters(self):
        """RdpCalssifier should pass alternate parameters to Java VM."""
        app = RdpClassifier()
        app.Parameters['-Xmx'].on('75M')
        exp = ''.join([
            'cd "', getcwd(), '/"; java -Xmx75M -jar "',
            self.user_rdp_jar_path, '" -q'])
        self.assertEqual(app.BaseCommand, exp)

    def test_basecommand_property(self):
        """RdpClassifier BaseCommand property should use overridden method."""
        app = RdpClassifier()
        self.assertEqual(app.BaseCommand, app._get_base_command())

    def test_base_command(self):
        """RdpClassifier should return expected shell command."""
        app = RdpClassifier()
        exp = ''.join([
            'cd "', getcwd(), '/"; java -Xmx1000m -jar "',
            self.user_rdp_jar_path, '" -q'])
        self.assertEqual(app.BaseCommand, exp)
        
    def test_change_working_dir(self):
        """RdpClassifier should run program in expected working directory."""
        test_dir = '/tmp/RdpTest'

        app = RdpClassifier(WorkingDir=test_dir)
        exp = ''.join([
            'cd "', test_dir, '/"; java -Xmx1000m -jar "',
            self.user_rdp_jar_path, '" -q'])
        self.assertEqual(app.BaseCommand, exp)

        rmtree(test_dir)

    def test_sample_fasta(self):
        """RdpClassifier should classify its own sample data correctly"""
        test_dir = '/tmp/RdpTest'
        app = RdpClassifier(WorkingDir=test_dir)
        _, output_fp = tempfile.mkstemp(dir=test_dir)
        app.Parameters['-o'].on(output_fp)        

        results = app(StringIO(rdp_sample_fasta))

        assignment_toks = results['Assignments'].readline().split('\t')

        self.assertEqual(assignment_toks[0], 'X67228')
        lineage = [x.strip('"') for x in assignment_toks[2::3]]
        self.assertEqual(lineage, [
            'Root', 'Bacteria', 'Proteobacteria', 'Alphaproteobacteria',
            'Rhizobiales', 'Rhizobiaceae', 'Rhizobium'])
        rmtree(test_dir)


class RdpTrainerTests(TestCase):
    """Tests of the trainer for the RdpClassifier app
    """

    def setUp(self):
        self.reference_file = StringIO(rdp_training_sequences)
        self.reference_file.seek(0)

        self.taxonomy_file = tempfile.NamedTemporaryFile(
            prefix="RdpTaxonomy", suffix=".txt")
        self.taxonomy_file.write(rdp_training_taxonomy)
        self.taxonomy_file.seek(0)

        self.training_dir = tempfile.mkdtemp(prefix='RdpTrainer_output_')

    def tearDown(self):
        rmtree(self.training_dir)

    def test_call(self):
        app = RdpTrainer()
        app.Parameters['taxonomy_file'] = self.taxonomy_file.name
        app.Parameters['model_output_dir'] = self.training_dir
        results = app(self.reference_file)

        exp_file_list = [
            'bergeyTrainingTree.xml', 'genus_wordConditionalProbList.txt',
            'logWordPrior.txt', 'RdpClassifier.properties',
            'wordConditionalProbIndexArr.txt',
            ]
        obs_file_list = listdir(self.training_dir)
        exp_file_list.sort()
        obs_file_list.sort()
        self.assertEqual(obs_file_list, exp_file_list)

        autogenerated_headers = {
            'bergeyTree': 'bergeyTrainingTree',
            'probabilityList': 'genus_wordConditionalProbList',
            'wordPrior': 'logWordPrior',
            'probabilityIndex': 'wordConditionalProbIndexArr',
            }
        for id, basename in autogenerated_headers.iteritems():
            obs_header = results[id].readline()
            exp_header = exp_training_header_template % basename
            self.assertEqual(exp_header, obs_header)


class RdpWrapperTests(TestCase):
    """ Tests of RDP classifier wrapper functions
    """
    def setUp(self):
        self.num_trials = 10
        
        self.test_input1 = rdp_test_fasta.split('\n')
        self.expected_assignments1 = rdp_expected_out
        
        # Files for training
        self.reference_file = StringIO(rdp_training_sequences)
        self.reference_file.seek(0)

        self.taxonomy_file = StringIO(rdp_training_taxonomy)
        self.taxonomy_file.seek(0)

        self.training_dir = tempfile.mkdtemp(prefix='RdpTrainer_output_')

        # Sequences for trained classifier
        self.test_trained_input = rdp_trained_fasta.split("\n")

    def tearDown(self):
        rmtree(self.training_dir)

    def test_parse_rdp_assignment(self):
        seqid, direction, assignments = parse_rdp_assignment(
            "X67228\t\t"
            "Root\tnorank\t1.0\t"
            "Bacteria\tdomain\t1.0\t"
            "\"Proteobacteria\"\tphylum\t1.0\t"
            "Alphaproteobacteria\tclass\t0.9\t"
            "Rhizobiales\torder\t0.9\t"
            "Rhizobiaceae\tfamily\t0.47\t"
            "Rhizobium\tgenus\t0.46")
        self.assertEqual(seqid, "X67228")

    def test_assign_taxonomy_short_sequence(self):
        """assign_taxonomy should return Unclassifiable if sequence is too short
        """
        assignments = assign_taxonomy([
            '>MySeq 1',
            'TTCCGGTTGATCCTGCCGGACCCGACTGCTATCCGGA',
            ])
        self.assertEqual(assignments, {'MySeq 1': ('Unassignable', 1.0)})
        
    def test_assign_taxonomy(self):
        """assign_taxonomy wrapper functions as expected 
        
            This test may fail periodicially, but failure should be rare.
        
        """
        
        unverified_seq_ids = set(self.expected_assignments1.keys())
        for i in range(self.num_trials):
            obs_assignments = assign_taxonomy(self.test_input1)
            for seq_id in list(unverified_seq_ids):
                obs_lineage, obs_confidence = obs_assignments[seq_id]
                exp_lineage = self.expected_assignments1[seq_id]
                if (obs_lineage == exp_lineage):
                    unverified_seq_ids.remove(seq_id)
            if not unverified_seq_ids:
                break

        messages = []
        for seq_id in unverified_seq_ids:
            messages.append("Unable to verify %s trials" % self.num_trials)
            messages.append("  Sequence ID: %s" % seq_id)
            messages.append("  Expected: %s" % self.expected_assignments1[seq_id])
            messages.append("  Observed: %s" % obs_assignments[seq_id][0])
            messages.append("  Confidence: %s" % obs_assignments[seq_id][1])
        
        # make sure all taxonomic results were correct at least once
        self.assertFalse(unverified_seq_ids, msg='\n'.join(messages))
            
    def test_assign_taxonomy_alt_confidence(self):
        """assign_taxonomy wrapper functions as expected with alt confidence
        """
        obs_assignments = assign_taxonomy(
            self.test_input1, min_confidence=0.95)            

        for seq_id, assignment in obs_assignments.items():
            obs_lineage, obs_confidence = assignment
            exp_lineage = self.expected_assignments1[seq_id]
            message = "Sequence ID: %s, assignment: %s" % (seq_id, assignment)
            self.assertTrue(
                exp_lineage.startswith(obs_lineage) or \
                (obs_lineage == "Unclassified"),
                msg=message,
                )
            self.assertTrue(obs_confidence >= 0.95, msg=message)
            
    def test_assign_taxonomy_file_output(self):
        """ assign_taxonomy wrapper writes correct file output when requested
        
            This function tests for sucessful completion of assign_taxonomy
             when writing to file, that the lines in the file roughly look
             correct by verifying how many are written (by zipping with 
             expected), and that each line starts with the correct seq id.
             Actual testing of taxonomy data is performed elsewhere.
        
        """
        output_fp = get_tmp_filename(\
         prefix='RDPAssignTaxonomyTests',suffix='.txt')
        # convert the expected dict to a list of lines to match 
        # file output
        expected_file_headers = self.expected_assignments1.keys()
        expected_file_headers.sort()
        
        actual_return_value = assign_taxonomy(\
         self.test_input1,min_confidence=0.95,output_fp=output_fp)
        
        actual_file_output = list(open(output_fp))
        actual_file_output.sort()

        # remove the output_fp before running the tests, so if they
        # fail the output file is still cleaned-up
        remove(output_fp)
        
        # None return value on write to file
        self.assertEqual(actual_return_value,None)
        
        # check that each line starts with the correct seq_id -- not 
        # checking the taxonomies or confidences here as these are variable and
        # tested elsewhere
        for a,e in zip(actual_file_output,expected_file_headers):
            self.assertTrue(a.startswith(e))

    def test_train_rdp_classifier(self):
        results = train_rdp_classifier(
            self.reference_file, self.taxonomy_file, self.training_dir)

        exp_file_list = [
            'bergeyTrainingTree.xml', 'genus_wordConditionalProbList.txt',
            'logWordPrior.txt', 'RdpClassifier.properties',
            'wordConditionalProbIndexArr.txt',
            ]
        obs_file_list = listdir(self.training_dir)
        exp_file_list.sort()
        obs_file_list.sort()
        self.assertEqual(obs_file_list, exp_file_list)

        autogenerated_headers = {
            'bergeyTree': 'bergeyTrainingTree',
            'probabilityList': 'genus_wordConditionalProbList',
            'wordPrior': 'logWordPrior',
            'probabilityIndex': 'wordConditionalProbIndexArr',
            }
        for id, basename in autogenerated_headers.iteritems():
            obs_header = results[id].readline()
            exp_header = exp_training_header_template % basename
            self.assertEqual(exp_header, obs_header)

    def test_train_rdp_classifier_and_assign_taxonomy(self):
        obs = train_rdp_classifier_and_assign_taxonomy(self.reference_file,
            self.taxonomy_file, self.test_trained_input, min_confidence=0.80,
            model_output_dir=self.training_dir)
        exp = {'X67228': (
            'Bacteria;Proteobacteria;Alphaproteobacteria;Rhizobiales;'
            'Rhizobiaceae;Rhizobium', 1.0
            )}
        self.assertEqual(obs, exp)

# Sample data copied from rdp_classifier-2.0, which is licensed under
# the GPL 2.0 and Copyright 2008 Michigan State University Board of
# Trustees

rdp_training_sequences = """>X67228 Bacteria;Proteobacteria;Alphaproteobacteria;Rhizobiales;Rhizobiaceae;Rhizobium
aacgaacgctggcggcaggcttaacacatgcaagtcgaacgctccgcaaggagagtggcagacgggtgagtaacgcgtgggaatctacccaaccctgcggaatagctctgggaaactggaattaataccgcatacgccctacgggggaaagatttatcggggatggatgagcccgcgttggattagctagttggtggggtaaaggcctaccaaggcgacgatccatagctggtctgagaggatgatcagccacattgggactgagacacggcccaaa
>X73443 Bacteria;Firmicutes;Clostridia;Clostridiales;Clostridiaceae;Clostridium
nnnnnnngagatttgatcctggctcaggatgaacgctggccggccgtgcttacacatgcagtcgaacgaagcgcttaaactggatttcttcggattgaagtttttgctgactgagtggcggacgggtgagtaacgcgtgggtaacctgcctcatacagggggataacagttagaaatgactgctaataccnnataagcgcacagtgctgcatggcacagtgtaaaaactccggtggtatgagatggacccgcgtctgattagctagttggtggggt
>AB004750 Bacteria;Proteobacteria;Gammaproteobacteria;Enterobacteriales;Enterobacteriaceae;Enterobacter
acgctggcggcaggcctaacacatgcaagtcgaacggtagcagaaagaagcttgcttctttgctgacgagtggcggacgggtgagtaatgtctgggaaactgcccgatggagggggataactactggaaacggtagctaataccgcataacgtcttcggaccaaagagggggaccttcgggcctcttgccatcggatgtgcccagatgggattagctagtaggtggggtaacggctcacctaggcgacgatccctagctggtctgagaggatgaccagccacactggaactgagacacggtccagactcctacgggaggcagcagtggggaatattgca
>xxxxxx Bacteria;Proteobacteria;Gammaproteobacteria;Pseudomonadales;Pseudomonadaceae;Pseudomonas
ttgaacgctggcggcaggcctaacacatgcaagtcgagcggcagcannnncttcgggaggctggcgagcggcggacgggtgagtaacgcatgggaacttacccagtagtgggggatagcccggggaaacccggattaataccgcatacgccctgagggggaaagcgggctccggtcgcgctattggatgggcccatgtcggattagttagttggtggggtaatggcctaccaaggcgacgatccgtagctggtctgagaggatgatcagccacaccgggactgagacacggcccggactcctacgggaggcagcagtggggaatattggacaatgggggcaaccctgatccagccatgccg
>AB004748 Bacteria;Proteobacteria;Gammaproteobacteria;Enterobacteriales;Enterobacteriaceae;Enterobacter
acgctggcggcaggcctaacacatgcaagtcgaacggtagcagaaagaagcttgcttctttgctgacgagtggcggacgggtgagtaatgtctgggaaactgcccgatggagggggataactactggaaacggtagctaataccgcataacgtcttcggaccaaagagggggaccttcgggcctcttgccatcggatgtgcccagatgggattagctagtaggtggggtaacggctcacctaggcgacgatccctagctggtctgagaggatgaccagccacactggaactgagacacggtccagactcctacgggaggcagcagtggggaatattgcacaatgggcgcaagcctgatgcagccatgccgcgtgtatgaagaaggccttcgggttg
>AB000278 Bacteria;Proteobacteria;Gammaproteobacteria;Vibrionales;Vibrionaceae;Photobacterium
caggcctaacacatgcaagtcgaacggtaanagattgatagcttgctatcaatgctgacgancggcggacgggtgagtaatgcctgggaatataccctgatgtgggggataactattggaaacgatagctaataccgcataatctcttcggagcaaagagggggaccttcgggcctctcgcgtcaggattagcccaggtgggattagctagttggtggggtaatggctcaccaaggcgacgatccctagctggtctgagaggatgatcagccacactggaactgagacacggtccagactcctacgggaggcagcagtggggaatattgcacaatgggggaaaccctgatgcagccatgccgcgtgta
>AB000390 Bacteria;Proteobacteria;Gammaproteobacteria;Vibrionales;Vibrionaceae;Vibrio
tggctcagattgaacgctggcggcaggcctaacacatgcaagtcgagcggaaacgantnntntgaaccttcggggnacgatnacggcgtcgagcggcggacgggtgagtaatgcctgggaaattgccctgatgtgggggataactattggaaacgatagctaataccgcataatgtctacggaccaaagagggggaccttcgggcctctcgcttcaggatatgcccaggtgggattagctagttggtgaggtaatggctcaccaaggcgacgatccctagctggtctgagaggatgatcagccacactggaactgag
"""

rdp_training_taxonomy = """\
1*Bacteria*0*0*domain
765*Firmicutes*1*1*phylum
766*Clostridia*765*2*class
767*Clostridiales*766*3*order
768*Clostridiaceae*767*4*family
769*Clostridium*768*5*genus
160*Proteobacteria*1*1*phylum
433*Gammaproteobacteria*160*2*class
586*Vibrionales*433*3*order
587*Vibrionaceae*586*4*family
588*Vibrio*587*5*genus
592*Photobacterium*587*5*genus
552*Pseudomonadales*433*3*order
553*Pseudomonadaceae*552*4*family
554*Pseudomonas*553*5*genus
604*Enterobacteriales*433*3*order
605*Enterobacteriaceae*604*4*family
617*Enterobacter*605*5*genus
161*Alphaproteobacteria*160*2*class
260*Rhizobiales*161*3*order
261*Rhizobiaceae*260*4*family
262*Rhizobium*261*5*genus"""

exp_training_header_template = "<trainsetNo>1</trainsetNo><version>version1</version><modversion>cogent</modversion><file>%s</file>\n"

rdp_trained_fasta = """>X67228
aacgaacgctggcggcaggcttaacacatgcaagtcgaacgctccgcaaggagagtggcagacgggtgagtaacgcgtgggaatctacccaaccctgcggaatagctctgggaaactggaattaataccgcatacgccctacgggggaaagatttatcggggatggatgagcccgcgttggattagctagttggtggggtaaaggcctaccaaggcgacgatccatagctggtctgagaggatgatcagccacattgggactgagacacggcccaaa
"""

rdp_sample_fasta = """>X67228 Bacteria;Proteobacteria;Alphaproteobacteria;Rhizobiales;Rhizobiaceae;Rhizobium
aacgaacgctggcggcaggcttaacacatgcaagtcgaacgctccgcaaggagagtggcagacgggtgagtaacgcgtgggaatctacccaaccctgcggaatagctctgggaaactggaattaataccgcatacgccctacgggggaaagatttatcggggatggatgagcccgcgttggattagctagttggtggggtaaaggcctaccaaggcgacgatccatagctggtctgagaggatgatcagccacattgggactgagacacggcccaaa
"""

rdp_sample_classification = """>X67228 reverse=false
Root; 1.0; Bacteria; 1.0; Proteobacteria; 1.0; Alphaproteobacteria; 1.0; Rhizobiales; 1.0; Rhizobiaceae; 1.0; Rhizobium; 0.95; 
"""

rdp_test_fasta = """>AY800210 description field
TTCCGGTTGATCCTGCCGGACCCGACTGCTATCCGGATGCGACTAAGCCATGCTAGTCTAACGGATCTTCGGATCCGTGGCATACCGCTCTGTAACACGTAGATAACCTACCCTGAGGTCGGGGAAACTCCCGGGAAACTGGGCCTAATCCCCGATAGATAATTTGTACTGGAATGTCTTTTTATTGAAACCTCCGAGGCCTCAGGATGGGTCTGCGCCAGATTATGGTCGTAGGTGGGGTAACGGCCCACCTAGCCTTTGATCTGTACCGGACATGAGAGTGTGTGCCGGGAGATGGCCACTGAGACAAGGGGCCAGGCCCTACGGGGCGCAGCAGGCGCGAAAACTTCACAATGCCCGCAAGGGTGATGAGGGTATCCGAGTGCTACCTTAGCCGGTAGCTTTTATTCAGTGTAAATAGCTAGATGAATAAGGGGAGGGCAAGGCTGGTGCCAGCCGCCGCGGTAAAACCAGCTCCCGAGTGGTCGGGATTTTTATTGGGCCTAAAGCGTCCGTAGCCGGGCGTGCAAGTCATTGGTTAAATATCGGGTCTTAAGCCCGAACCTGCTAGTGATACTACACGCCTTGGGACCGGAAGAGGCAAATGGTACGTTGAGGGTAGGGGTGAAATCCTGTAATCCCCAACGGACCACCGGTGGCGAAGCTTGTTCAGTCATGAACAACTCTACACAAGGCGATTTGCTGGGACGGATCCGACGGTGAGGGACGAAACCCAGGGGAGCGAGCGGGATTAGATACCCCGGTAGTCCTGGGCGTAAACGATGCGAACTAGGTGTTGGCGGAGCCACGAGCTCTGTCGGTGCCGAAGCGAAGGCGTTAAGTTCGCCGCCAGGGGAGTACGGCCGCAAGGCTGAAACTTAAAGGAATTGGCGGGGGAGCAC
>EU883771
TGGCGTACGGCTCAGTAACACGTGGATAACTTACCCTTAGGACTGGGATAACTCTGGGAAACTGGGGATAATACTGGATATTAGGCTATGCCTGGAATGGTTTGCCTTTGAAATGTTTTTTTTCGCCTAAGGATAGGTCTGCGGCTGATTAGGTCGTTGGTGGGGTAATGGCCCACCAAGCCGATGATCGGTACGGGTTGTGAGAGCAAGGGCCCGGAGATGGAACCTGAGACAAGGTTCCAGACCCTACGGGGTGCAGCAGGCGCGAAACCTCCGCAATGTACGAAAGTGCGACGGGGGGATCCCAAGTGTTATGCTTTTTTGTATGACTTTTCATTAGTGTAAAAAGCTTTTAGAATAAGAGCTGGGCAAGACCGGTGCCAGCCGCCGCGGTAACACCGGCAGCTCGAGTGGTGACCACTTTTATTGGGCTTAAAGCGTTCGTAGCTTGATTTTTAAGTCTCTTGGGAAATCTCACGGCTTAACTGTGAGGCGTCTAAGAGATACTGGGAATCTAGGGACCGGGAGAGGTAAGAGGTACTTCAGGGGTAGAAGTGAAATTCTGTAATCCTTGAGGGACCACCGATGGCGAAGGCATCTTACCAGAACGGCTTCGACAGTGAGGAACGAAAGCTGGGGGAGCGAACGGGATTAGATACCCCGGTAGTCCCAGCCGTAAACTATGCGCGTTAGGTGTGCCTGTAACTACGAGTTACCGGGGTGCCGAAGTGAAAACGTGAAACGTGCCGCCTGGGAAGTACGGTCGCAAGGCTGAAACTTAAAGGAATTGGCGGGGGAGCACCACAACGGGTGGAGCCTGCGGTTTAATTGGACTCAACGCCGGGCAGCTCACCGGATAGGACAGCGGAATGATAGCCGGGCTGAAGACCTTGCTTGACCAGCTGAGA
>EF503699
AAGAATGGGGATAGCATGCGAGTCACGCCGCAATGTGTGGCATACGGCTCAGTAACACGTAGTCAACATGCCCAGAGGACGTGGACACCTCGGGAAACTGAGGATAAACCGCGATAGGCCACTACTTCTGGAATGAGCCATGACCCAAATCTATATGGCCTTTGGATTGGACTGCGGCCGATCAGGCTGTTGGTGAGGTAATGGCCCACCAAACCTGTAACCGGTACGGGCTTTGAGAGAAGGAGCCCGGAGATGGGCACTGAGACAAGGGCCCAGGCCCTATGGGGCGCAGCAGGCACGAAACCTCTGCAATAGGCGAAAGCTTGACAGGGTTACTCTGAGTGATGCCCGCTAAGGGTATCTTTTGGCACCTCTAAAAATGGTGCAGAATAAGGGGTGGGCAAGTCTGGTGTCAGCCGCCGCGGTAATACCAGCACCCCGAGTTGTCGGGACGATTATTGGGCCTAAAGCATCCGTAGCCTGTTCTGCAAGTCCTCCGTTAAATCCACCCGCTTAACGGATGGGCTGCGGAGGATACTGCAGAGCTAGGAGGCGGGAGAGGCAAACGGTACTCAGTGGGTAGGGGTAAAATCCTTTGATCTACTGAAGACCACCAGTGGTGAAGGCGGTTCGCCAGAACGCGCTCGAACGGTGAGGATGAAAGCTGGGGGAGCAAACCGGAATAGATACCCGAGTAATCCCAACTGTAAACGATGGCAACTCGGGGATGGGTTGGCCTCCAACCAACCCCATGGCCGCAGGGAAGCCGTTTAGCTCTCCCGCCTGGGGAATACGGTCCGCAGAATTGAACCTTAAAGGAATTTGGCGGGGAACCCCCACAAGGGGGAAAACCGTGCGGTTCAATTGGAATCCACCCCCCGGAAACTTTACCCGGGCGCG
>random_seq
AAGCTCCGTCGCGTGAGCTAAAAACCATGCTGACTTATGAGACCTAAAAGCGATGCGCCGACCTGACGATGCTCTGTTCAGTTTCATCACGATCACCGGTAGTCAGGGTACCCTCCAGACCGCGCATAGTGACTATGTTCCCGCACCTGTATATGTAATTCCCATTATACGTCTACGTTATGTAGTAAAGTTGCTCACGCCAGGCACAGTTTGTCTTGATACATAGGGTAGCTTAAGTCCCGTCCATTTCACCGCGATTGTAATAGACGAATCAGCAGTGGTGCAATCAAGTCCCAACAGTTATATTTCAAAAATCTTCCGATAGTCGTGGGCGAAGTTGTCAACCTACCTACCATGGCTATAAGGCCCAGTTTACTTCAGTTGAACGTGACGGTAACCCTACTGAGTGCACGATACCTGCTCAACAACGGCCCAAAACCCGTGCGACACATTGGGCACTACAATAATCTTAGAGGACCATGGATCTGGTGGGTGGACTGAAGCATATCCCAAAAGTGTCGTGAGTCCGTTATGCAATTGACTGAAACAGCCGTACCAGAGTTCGGATGACCTCTGGGTTGCTGCGGTACACACCCGGGTGCGGCTTCTGAAATAGAAAAGACTAAGCATCGGCCGCCTCACACGCCAC
>DQ260310
GATACCCCCGGAAACTGGGGATTATACCGGATATGTGGGGCTGCCTGGAATGGTACCTCATTGAAATGCTCCCGCGCCTAAAGATGGATCTGCCGCAGAATAAGTAGTTTGCGGGGTAAATGGCCACCCAGCCAGTAATCCGTACCGGTTGTGAAAACCAGAACCCCGAGATGGAAACTGAAACAAAGGTTCAAGGCCTACCGGGCACAACAAGCGCCAAAACTCCGCCATGCGAGCCATCGCGACGGGGGAAAACCAAGTACCACTCCTAACGGGGTGGTTTTTCCGAAGTGGAAAAAGCCTCCAGGAATAAGAACCTGGGCCAGAACCGTGGCCAGCCGCCGCCGTTACACCCGCCAGCTCGAGTTGTTGGCCGGTTTTATTGGGGCCTAAAGCCGGTCCGTAGCCCGTTTTGATAAGGTCTCTCTGGTGAAATTCTACAGCTTAACCTGTGGGAATTGCTGGAGGATACTATTCAAGCTTGAAGCCGGGAGAAGCCTGGAAGTACTCCCGGGGGTAAGGGGTGAAATTCTATTATCCCCGGAAGACCAACTGGTGCCGAAGCGGTCCAGCCTGGAACCGAACTTGACCGTGAGTTACGAAAAGCCAAGGGGCGCGGACCGGAATAAAATAACCAGGGTAGTCCTGGCCGTAAACGATGTGAACTTGGTGGTGGGAATGGCTTCGAACTGCCCAATTGCCGAAAGGAAGCTGTAAATTCACCCGCCTTGGAAGTACGGTCGCAAGACTGGAACCTAAAAGGAATTGGCGGGGGGACACCACAACGCGTGGAGCCTGGCGGTTTTATTGGGATTCCACGCAGACATCTCACTCAGGGGCGACAGCAGAAATGATGGGCAGGTTGATGACCTTGCTTGACAAGCTGAAAAGGAGGTGCAT
>EF503697
TAAAATGACTAGCCTGCGAGTCACGCCGTAAGGCGTGGCATACAGGCTCAGTAACACGTAGTCAACATGCCCAAAGGACGTGGATAACCTCGGGAAACTGAGGATAAACCGCGATAGGCCAAGGTTTCTGGAATGAGCTATGGCCGAAATCTATATGGCCTTTGGATTGGACTGCGGCCGATCAGGCTGTTGGTGAGGTAATGGCCCACCAAACCTGTAACCGGTACGGGCTTTGAGAGAAGTAGCCCGGAGATGGGCACTGAGACAAGGGCCCAGGCCCTATGGGGCGCAGCAGGCGCGAAACCTCTGCAATAGGCGAAAGCCTGACAGGGTTACTCTGAGTGATGCCCGCTAAGGGTATCTTTTGGCACCTCTAAAAATGGTGCAGAATAAGGGGTGGGCAAGTCTGGTGTCAGCCGCCGCGGTAATACCAGCACCCCGAGTTGTCGGGACGATTATTGGGCCTAAAGCATCCGTAGCCTGTTCTGCAAGTCCTCCGTTAAATCCACCTGCTCAACGGATGGGCTGCGGAGGATACCGCAGAGCTAGGAGGCGGGAGAGGCAAACGGTACTCAGTGGGTAGGGGTAAAATCCATTGATCTACTGAAGACCACCAGTGGCGAAGGCGGTTTGCCAGAACGCGCTCGACGGTGAGGGATGAAAGCTGGGGGAGCAAACCGGATTAGATACCCGGGGTAGTCCCAGCTGTAAACGGATGCAGACTCGGGTGATGGGGTTGGCTTCCGGCCCAACCCCAATTGCCCCCAGGCGAAGCCCGTTAAGATCTTGCCGCCCTGTCAGATGTCAGGGCCGCCAATACTCGAAACCTTAAAAGGAAATTGGGCGCGGGAAAAGTCACCAAAAGGGGGTTGAAACCCTGCGGGTTATATATTGTAAACC
>short_seq
TAAAATGACTAGCCTGCGAGTCAC
"""

rdp_expected_out = {
    'AY800210 description field': 'Archaea;Euryarchaeota',
    'EU883771': 'Archaea;Euryarchaeota;Methanomicrobia;Methanomicrobiales;Methanomicrobiaceae;Methanomicrobium',
    'EF503699': 'Archaea;Crenarchaeota;Thermoprotei',
    'random_seq': 'Bacteria',
    'DQ260310': 'Archaea;Euryarchaeota;Methanobacteria;Methanobacteriales;Methanobacteriaceae;Methanosphaera',
    'EF503697': 'Archaea;Crenarchaeota;Thermoprotei',
    'short_seq': 'Unassignable',
    }

if __name__ == '__main__':
    main()
