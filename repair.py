"""
Automated program repair ::
"""
import re
import os
import sys
import random
import argparse
import time
from pyggi.base import Patch, AbstractProgram
from pyggi.line import LineProgram
from pyggi.line import LineReplacement, LineInsertion, LineDeletion
from pyggi.tree import TreeProgram
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion
from pyggi.algorithms import LocalSearch
from termcolor import colored

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
            result.status = 'INVALID'
            result.fitness = 2
            return
        
        if m_fail or m_pass: #or m_time:
            # time = float(m_time[0]) if len(m_time) > 0 else 0
            
            failed = int(m_fail[0]) if len(m_fail) > 0 else 0
            passed = int(m_pass[0]) if len(m_pass) > 0 else 0
            result.fitness = failed / (failed + passed) if failed + passed > 0 else 1
            
            if result.fitness == 0:
                result.status = 'SUCCESS'
            else:
                result.status = 'FAIL TEST: ' + str(failed) + '/' + str(failed + passed)
        else:
            result.fitness = 1
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
        if fitness is None:
            return False
        if best_fitness is None:
            return True
        return fitness < best_fitness

    def stopping_criterion(self, iter, fitness):
        return fitness == 0
    
    def run(self, warmup_reps=1, epoch=5, max_iter=100, timeout=15, verbose=True):
        if verbose:
            self.program.logger.info(self.program.logger.log_file_path)

        warmup = list()
        empty_patch = Patch(self.program)
        for i in range(warmup_reps):
            result = self.program.evaluate_patch(empty_patch, timeout=timeout)
            if result.status != 'INVALID':
                warmup.append(result.fitness)
        original_fitness = float(sum(warmup)) / len(warmup) if warmup else None

        if verbose:
            self.program.logger.info(
                "The fitness value of original program: {}".format(original_fitness))

        result = []

        if verbose:
            self.program.logger.info("Epoch\tIter\tStatus\tFitness\tPatch")

        for cur_epoch in range(1, epoch + 1):
            # Reset Search
            self.setup()
            cur_result = {}
            best_patch = empty_patch
            best_fitness = original_fitness

            # Result Initilization
            cur_result['BestPatch'] = None
            cur_result['Success'] = False
            cur_result['FitnessEval'] = 0
            cur_result['InvalidPatch'] = 0
            cur_result['diff'] = None
            cur_result['BestFitness'] = original_fitness

            start = time.time()
            for cur_iter in range(1, max_iter + 1):
                patch = self.get_neighbour(best_patch.clone())
                run = self.program.evaluate_patch(patch, timeout=timeout)
                cur_result['FitnessEval'] += 1

                if run.status == 'INVALID' or run.status == 'TIMEOUT':
                    cur_result['InvalidPatch'] += 1
                    update_best = False
                else:
                    update_best = self.is_better_than_the_best(run.fitness, best_fitness)

                if update_best:
                    best_fitness, best_patch = run.fitness, patch
                    cur_result['BestFitness'] = best_fitness

                if verbose:
                    color = 'green' if run.status == 'SUCCESS' else 'yellow'
                    if run.status == 'INVALID':
                        color = 'red'
                    self.program.logger.info(colored("{}\t{}\t{}\t{}{}\t{}", color).format(
                        cur_epoch, cur_iter, run.status, '*' if update_best else '',
                        run.fitness, patch))

                if run.fitness is not None and self.stopping_criterion(cur_iter, run.fitness):
                    cur_result['Success'] = True
                    break

            cur_result['Time'] = time.time() - start

            if best_patch:
                cur_result['BestPatch'] = best_patch
                cur_result['BestFitness'] = best_fitness
                cur_result['diff'] = self.program.diff(best_patch)

            result.append(cur_result)
        return result

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PYGGI QuixBug Repair')
    parser.add_argument('--project_path', type=str, default='repairs/')
    parser.add_argument('--config', type=str, default=None)
    parser.add_argument('--target', type=str, default=None,
                        help='target bug and language to repair, if the config file does not exist, this argument will be used to create a new config file')
    parser.add_argument('--mode', type=str, default='line')
    parser.add_argument('--epoch', type=int, default=20,
        help='total epoch(default: 20)')
    parser.add_argument('--iter', type=int, default=400,
        help='total iterations per epoch(default: 400)')
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
                        template = "\n{{\n    \"target_files\": [\n        \"QuixBugs/{target_lang}_programs/{target_bug}.py\"\n    ],\n    \"test_command\": \"pytest QuixBugs/{target_lang}_testcases/test_{target_bug}.py\"\n}}\n"
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
                        print(f"*****************Config file \'{config_file}\' created.*****************")
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

    results = tabu_search.run(warmup_reps=1, epoch=args.epoch, max_iter=args.iter, timeout=10)
    
    success_results = [res for res in results if res['Success']]
    fit_evals = [res['FitnessEval'] for res in success_results if res['Success']]
    
    print("======================RESULTS======================")
    for res in results:
        print('----------------------------------------')
        print('Success:', res['Success'])
        print('Fitted on iteration:', res['FitnessEval'])
        print('Invalid Patch:', res['InvalidPatch'])
        print('Fitness:', res['BestFitness'])
        print('Diff: \n', res['diff'])
        print('----------------------------------------\n')
    
    unique_diffs = set([res['diff'] for res in success_results])
    print(colored("======================SUCCESS PATCHES======================\n", 'green'))
    n = 0
    for res in unique_diffs:
        print(colored('----------------------------------------\n', 'green'))
        print(res)
        print(colored('----------------------------------------\n', 'green'))
        n += 1
    print(n, 'types of success patches found.')
    success_count = len(success_results)
    result_count = len(results)
    print(f"Success rate: {success_count/result_count*100}% ({success_count}/{result_count})")
    avg_fit_evals = 0
    if(len(fit_evals) != 0):
        avg_fit_evals = int(sum(fit_evals)/len(fit_evals))
    print(f"Average iterations need to success: {avg_fit_evals}")
    program.remove_tmp_variant()