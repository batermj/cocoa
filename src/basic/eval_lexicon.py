import argparse
import collections
import json
import os
import re
import time

from lexicon import Lexicon
from schema import Schema

"""
Runs lexicon on transcripts of MTurk conversations and entity annotated dataset
"""

parser = argparse.ArgumentParser()
parser.add_argument("--schema-path", help="Path to schema file governs scenarios",
                    type=str)
parser.add_argument("--transcripts-path", help="Json of all examples", type=str)
parser.add_argument("--scenarios-json", help="Json of scenario information", type=str)
parser.add_argument("--annotated-examples-path", help="Json of annotated examples", type=str)
args = parser.parse_args()


def compute_f1(total_tp, total_fp, total_fn):
    precision = total_tp / (total_tp + total_fp)
    recall = total_tp / (total_tp + total_fn)

    return 2. * precision * recall / (precision + recall), precision, recall


def get_tp_fp_fn(gold_annotation, candidate_annotation):
    """
    Get the true positive, false positive, and false negative for the sets
    :param gold_annotation:
    :param candidate_annotation:
    :return:
    """
    tp, fp, fn = 0., 0., 0.
    for c in candidate_annotation:
        if c in gold_annotation:
            tp += 1
        else:
            fp += 1

    for g in gold_annotation:
        if g not in candidate_annotation:
            fn += 1

    # How to handle empty gold and candidate sets?

    return tp, fp, fn


def entity_link_examples_file(lexicon, examples_infile, processed_outfile, re_pattern):
    """
    Processes examples in given file, entity linking with the provided lexicon
    :param lexicon: Lexicon being used for linking
    :param examples_infile: Path to file with examples
    :return:
    """
    with open(examples_infile, "r") as f:
        examples = json.load(f)

    outfile = open(processed_outfile, "w")

    for ex in examples:
        events = ex["events"]

        num_sentences = 0
        for e in events:
            agent = e["agent"]
            msg_data = e["data"]
            action = e["action"]
            if action == "message":
                if msg_data != None:
                    num_sentences += 1
                    raw_tokens = re.findall(re_pattern, msg_data)
                    lower_raw_tokens = [r.lower() for r in raw_tokens]
                    outfile.write("Agent {0}: ".format(agent) + msg_data + "\n")
                    linked = lexicon.entitylink(lower_raw_tokens, return_entities=True)

                    outfile.write("Linked: " + str(linked) + "\n\n")
                    outfile.write("-"*10 + "\n")

    outfile.close()


def eval_lexicon(lexicon, examples, re_pattern):
    """
    Evaluate lexicon given list of examples
    :param lexicon:
    :param examples:
    :return:
    """
    total_num_annotations = 0
    total_num_sentences = 0
    total_tp, total_fp, total_fn = 0., 0., 0.
    for ex in examples:
        for e in ex["events"]:
            msg_data = e["data"]
            action = e["action"]
            if action == "message":
                total_num_sentences += 1

                gold_annotation = []
                for a in e["entityAnnotation"]:
                    span = re.sub("-|\.", " ", a["span"].lower()).strip()
                    entity = a["entity"].lower()
                    gold_annotation.append((span, entity))

                raw_tokens = re.findall(re_pattern, msg_data)
                lower_raw_tokens = [r.lower() for r in raw_tokens]
                linked, candidate_annotation = lexicon.entitylink(lower_raw_tokens, return_entities=True)

                total_num_annotations += len(gold_annotation)
                tp, fp, fn = get_tp_fp_fn(gold_annotation, candidate_annotation)
                total_tp += tp
                total_fp += fp
                total_fn += fn
                # Output mistakes to stdout
                if fp >= 1 or fn >= 1:
                    print msg_data
                    print "gold: ", gold_annotation
                    print "candidate: ", candidate_annotation
                    print "TP: {0}, FP: {1}, FN: {2}".format(tp, fp, fn)
                    print "-"*10

    avg_f1, avg_precision, avg_recall = compute_f1(total_tp, total_fp, total_fn)
    print "Avg f1 over {0} annotations: {1}, {2}, {3}".format(total_num_annotations,
                                                              avg_f1, avg_precision, avg_recall)

    return avg_f1


if __name__ == "__main__":
    re_pattern = r"<|>|[(\w*)]+|[\w]+|\.|\(|\)|\\|\"|\/|;|\#|\&|\$|\%|\@|\{|\}|\:"
    schema = Schema(args.schema_path)

    start = time.time()
    with open(args.scenarios_json, "r") as f:
        scenarios_info = json.load(f)

    with open(args.annotated_examples_path, "r") as f:
        examples = json.load(f)


    output_dir = os.path.dirname(os.path.dirname(os.getcwd())) + "/output"
    lexicon = Lexicon(schema)

    eval_lexicon(lexicon, examples, re_pattern)
    print "Total time: ", time.time() - start
