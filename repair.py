"""
Automated program repair ::
"""
import re
import os
import sys
import random
import argparse
from pyggi.base import Patch, AbstractProgram
from pyggi.line import LineProgram
from pyggi.line import LineReplacement, LineInsertion, LineDeletion
from pyggi.tree import TreeProgram
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion
from pyggi.algorithms import LocalSearch

class QuixProgram(AbstractProgram):
    def compute_fitness(self, result, return_code, stdout, stderr, elapsed_time):
        org_stdout = stdout
        stdout = stdout[:-1]
        stdout = stdout[stdout.rfind("\n")+1:]
        stdout = stdout.replace("=", "").strip()
        m_fail = re.findall("([0-9]+) failed", stdout)
        m_pass = re.findall("([0-9]+) passed", stdout)
        m_error = re.findall("([0-9]+) error", stdout)
        # m_time = re.findall("in ([0-9]+\.[0-9]+)s", stdout)
        if len(m_error) > 0:
            result.status = 'CODE_ERROR'
            result.fitness = 1
            return
        
        if m_fail or m_pass: #or m_time:
            # time = float(m_time[0]) if len(m_time) > 0 else 0
            failed = int(m_fail[0]) if len(m_fail) > 0 else 0
            passed = int(m_pass[0]) if len(m_pass) > 0 else 0
            result.fitness = failed / (failed + passed) if failed + passed > 0 else 1
        else:
            result.status = 'PARSE_ERROR'
            print("STDOUT:", org_stdout)

class QuixLineProgram(LineProgram, QuixProgram):
    pass

class QuixTreeProgram(TreeProgram, QuixProgram):
    pass

class QuixTabuSearch(LocalSearch):
    def setup(self):
        self.tabu = []

    def get_neighbour(self, patch):
        while True:
            temp_patch = patch.clone()
            if len(temp_patch) > 0 and random.random() < 0.5:
                temp_patch.remove(random.randrange(0, len(temp_patch)))
            else:
                edit_operator = random.choice(self.operators)
                temp_patch.add(edit_operator.create(self.program, method="weighted"))
            if not any(item == temp_patch for item in self.tabu):
                self.tabu.append(temp_patch)
                break
        return temp_patch

    def is_better_than_the_best(self, fitness, best_fitness):
        if best_fitness is None:
            return True
        return fitness < best_fitness

    def stopping_criterion(self, iter, fitness):
        return fitness == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PYGGI QuixBug Repair')
    parser.add_argument('--project_path', type=str, default='repairs/')
    parser.add_argument('--config', type=str, default=None)
    parser.add_argument('--target', type=str, default=None,
                        help='target bug and language to repair, if the config file does not exist, this argument will be used to create a new config file')
    parser.add_argument('--mode', type=str, default='tree')
    parser.add_argument('--epoch', type=int, default=10,
        help='total epoch(default: 10)')
    parser.add_argument('--iter', type=int, default=100,
        help='total iterations per epoch(default: 100)')
    args = parser.parse_args()
    assert args.mode in ['line', 'tree']

    if args.config and args.target:
        raise Exception("Please specify either config file or target, not both")

    config_file = args.config
    if args.config:
        if not os.path.exists(os.path.join(os.getcwd(), args.project_path, args.config)):
            raise Exception(f"Config file \'{args.config}\' not found")

    if args.target:
        # If the corresponding config file exists, use the config file
        if os.path.exists(os.path.join(os.getcwd(), args.project_path, args.target + '.pyggi.config')):
            config_file = args.target + '.pyggi.config'
        # If the corresponding config file does not exist, try create a new config file
        else:        
            target = args.target.split('-')
            if len(target) == 2:
                target_bug, target_lang = target
                
                if target_lang not in ['python', 'java']:
                    raise Exception(f"Invalid target language \'{target_lang}\', Please use either \'python\' or \'java\'")
                
                validation_path = os.path.join(os.getcwd(), args.project_path, "QuixBugs/", target_lang + "_programs/", target_bug + ".py")
                if not os.path.exists(validation_path):
                    raise Exception(f"Invalid target \'{args.target}\', Please name your target as \'[bug]-[language]\' with the same name as the QuixBugs repo then try again")
                else:
                    if target_lang == 'python':
                        template = "\n{{\n    \"target_files\": [\n        \"QuixBugs/{target_lang}_programs/{target_bug}.py\"\n    ],\n    \"test_command\": \"pytest -s QuixBugs/{target_lang}_testcases/test_{target_bug}.py\"\n}}\n"
                    elif target_lang == 'java':
                        # TODO: add java template
                        raise NotImplementedError("Java template not implemented yet 😭")
                        pass
                    else:
                        raise Exception(f"Invalid target language \'{target_lang}\', Please use either \'python\' or \'java\'")
                    template = template.format(target_lang=target_lang, target_bug=target_bug)
                    config_file = f"{target_bug}-{target_lang}" + '.pyggi.config'
                    with open(os.path.join(os.getcwd(), args.project_path, config_file), 'w') as f:
                        f.write(template)
            else:
                raise Exception(f"Invalid target \'{args.target}\', Please name your target as \'[bug]-[language]\' then try again")

    if args.mode == 'line':
        program = QuixLineProgram(args.project_path, config=config_file)
        tabu_search = QuixTabuSearch(program)
        tabu_search.operators = [LineReplacement, LineInsertion, LineDeletion]
    elif args.mode == 'tree':
        program = QuixTreeProgram(args.project_path, config=config_file)
        tabu_search = QuixTabuSearch(program)
        tabu_search.operators = [StmtReplacement, StmtInsertion, StmtDeletion]

    result = tabu_search.run(warmup_reps=1, epoch=args.epoch, max_iter=args.iter, timeout=10)
    
    success_results = [res for res in result if res['Success']]
    print("======================RESULTS======================")
    for res in result:
        print('----------------------------------------')
        print('Success:', res['Success'])
        print('Fitted at iteration:', res['FitnessEval'])
        print('Invalid Patch:', res['InvalidPatch'])
        print('Diff: \n', res['diff'])
        print('----------------------------------------\n')
    
    unique_diffs = set([res['diff'] for res in success_results])
    print("======================SUCCESS PATCHES======================")
    n = 0
    for res in unique_diffs:
        print('----------------------------------------\n')
        print(res)
        print('----------------------------------------\n')
        n += 1
    print(n, 'types of success patches found.')
    program.remove_tmp_variant()