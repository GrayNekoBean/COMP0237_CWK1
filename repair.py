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
        stdout = stdout[:-1]
        stdout = stdout[stdout.rfind("\n")+1:]
        stdout = stdout.replace("=", "").strip()
        m = re.findall("([0-9]+) failed, ([0-9]+) passed in ([0-9]+\.[0-9]+)s", stdout)
        m = m[0] if len(m) > 0 else []
        if len(m) > 0:
            runtime = float(m[2])
            failed = int(m[0])
            passed = int(m[1])
            result.fitness = failed / (failed + passed)
        else:
            result.status = 'PARSE_ERROR'

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
        return fitness < best_fitness

    def stopping_criterion(self, iter, fitness):
        return fitness == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PYGGI QuixBug Repair')
    parser.add_argument('--project_path', type=str, default='repairs/')
    parser.add_argument('--config', type=str, default='.pyggi.config')
    parser.add_argument('--target', type=str, default='quixbugs')
    parser.add_argument('--mode', type=str, default='tree')
    parser.add_argument('--epoch', type=int, default=10,
        help='total epoch(default: 30)')
    parser.add_argument('--iter', type=int, default=10,
        help='total iterations per epoch(default: 100)')
    args = parser.parse_args()
    assert args.mode in ['line', 'tree']

    config_file = args.config
    if args.config:
        if not os.path.exists(os.path.join(os.getcwd(), args.project_path, args.config)):
            raise Exception(f"Config file \'{args.config}\' not found")

    if args.mode == 'line':
        program = QuixLineProgram(args.project_path, config=config_file)
        tabu_search = QuixTabuSearch(program)
        tabu_search.operators = [LineReplacement, LineInsertion, LineDeletion]
    elif args.mode == 'tree':
        program = QuixTreeProgram(args.project_path, config=config_file)
        tabu_search = QuixTabuSearch(program)
        tabu_search.operators = [StmtReplacement, StmtInsertion, StmtDeletion]

    result = tabu_search.run(warmup_reps=1, epoch=args.epoch, max_iter=args.iter, timeout=10)
    
    success_result = [res for res in result if res['Success']]
    print("======================RESULT======================")
    for res in result:
        print('========================================')
        print('Success:', res['Success'])
        print('Fitness:', res['FitnessEval'])
        print('Invalid Patch:', res['InvalidPatch'])
        print('Diff: \n', res['diff'])
        print('----------------------------------------')
    
    print("======================SUCCESS RESULT======================")
    for res in success_result:
        print('========================================')
        print('Success:', res['Success'])
        print('Fitness:', res['FitnessEval'])
        print('Invalid Patch:', res['InvalidPatch'])
        print('Diff: \n', res['diff'])
        print('----------------------------------------')
    program.remove_tmp_variant()
