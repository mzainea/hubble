# -*- encoding: utf-8 -*-
"""
List type comparator used to match a list input with expected output

Comparators are used by Audit module to compare module output 
with the expected result
In FDG-connector, comparators might also be used with FDG

List comparator exposes various commands:

- "size"
    To check the size of list

    comparator:
        type: "list"
        size: ">= 10"
    # Supported operators >, >=, <, <=, ==, !=
    # it can also be written as (without any operator)
    # size: 10

- "match"
    True when the given list matches exactly with the expected list

    comparator:
        type: "list"
        match:
            - name: abc
              running: false

- "match_any"
    True when any dictionary mentioned in list match

    comparator:
        type: "list"
        match_any:
            - name: abc
              running: false
            - name: xyz
              running: true

- "match_all"
    True when all dictionaries mentioned in list matches with input

    comparator:
        type: "list"
        match_all:
            - name: abc
              running: false
            - name: xyz
              running: true

- "match_any_if_keyvalue_matches"
    This is a special case when user want to match only when desired key is found.
    Example: If name=rsync found, then match other attributes.
  
  Result will be True 
    - if specified key not found.
    - key found and attributes also matched
  Result will be False
    - Key found and attributes did not match

    comparator:
        type: "list"
        match_any_if_keyvalue_matches:
            match_key: name
            args:
                - name: abc
                  running: false
                - name: xyz
                  running: true

- "filter_compare"
    example (Filter a list, compare it with any other command of list comparator)

    comparator:
        type: "list"
        filter_compare:
            filter:
                name: abc
                offset:
                    type: number
                    match: <= 15
            compare:
                size: >= 4


Complete Example
------------------

check_id:
  description: 'sample description'
  tag: 'ADOBE-00041'
  implementations:
    - filter:
        grains: 'G@osfinger:CentOS*Linux-7'
      module: service
      items:
        - args:
            name: 'abc*'
          comparator:
            type: "list"
            match_any:
                - name: abc2
                    status: true
                - name: xyz
                    status: false
"""

import logging
import hubblestack.module_runner.comparator
import hubblestack.module_runner.runner_utils as runner_utils

log = logging.getLogger(__name__)


def size(audit_id, result_to_compare, args):
    """
    Check size of a list

    :param result_to_compare:
        The value to compare.
    :param args:
        Comparator dictionary as mentioned in the check.
    """
    log.debug('Running list::size for check: {0}'.format(audit_id))

    # Use Number comparator to do this comparison
    ret_status, ret_val = hubblestack.module_runner.comparator.run(
        audit_id,
        {"type": "number", "match": args['size']},
        len(result_to_compare))

    if ret_status:
        return True, "Check Passed"
    return False, "list::size failure. Expected={0} Got={1}".format(len(result_to_compare), str(args['size']))


def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def match(audit_id, result_to_compare, args):
    """
    Exact match the given list with result
    True only if lists are exactly equal
    :param audit_id:
        check id
    :param result_to_compare:
        The value to compare
    :param args:
        Comparator dict mentioned in check
    :return:
    """
    log.debug('Running list::match for check: {0}'.format(audit_id))
    expected_list = args.get('match')
    if not isinstance(result_to_compare, list) or len(result_to_compare) == 0:
        log.error("empty list received in list::match for audit_id: {0}".format(audit_id))
        return False, "list::match failure. {0} is not an instance of list".format(result_to_compare)
    if is_integer(result_to_compare[0]):
        ret_status, ret_val = hubblestack.module_runner.comparator.run(
            audit_id,
            {"type": "number", "match": expected_list[0]},
            int(result_to_compare[0]))
        if ret_status:
            return True, "Check Passed"
    if isinstance(result_to_compare[0], dict):
        # If list to compare has dict, it uses first key of dict to sort list
        sort_key = list(result_to_compare[0].keys())[0]
        result_to_compare.sort(key=lambda i: i[sort_key])
        expected_list.sort(key=lambda i: i[sort_key])
    else:
        # Other data types. Simply sort the list
        result_to_compare.sort()
        expected_list.sort()
    if result_to_compare == expected_list:
        return True, "Check Passed"
    return False, "list::match failure. Got={0}".format(result_to_compare)


def match_any(audit_id, result_to_compare, args):
    """
    Match any of dictionary mentioned. Match only mentioned attributes
    True if found any entry

    :param result_to_compare:
        The value to compare.
    :param args:
        Comparator dictionary as mentioned in the check.
    """
    log.debug('Running list::match_any for check: {0}'.format(audit_id))

    ignore_case = args.get('ignore_case', False)
    for r_compare in result_to_compare:
        if is_integer(r_compare):
            ret_status, ret_val = hubblestack.module_runner.comparator.run(
                audit_id,
                {"type": "number", "match_any": args['match_any']},
                int(r_compare))
            if ret_status:
                return True, "Check Passed"
        if isinstance(r_compare, dict):
            # using dict::match_any
            ret_status, ret_val = hubblestack.module_runner.comparator.run(
                audit_id,
                {"type": "dict", "match_any": args['match_any'], "ignore_case": ignore_case},
                r_compare)
            if ret_status:
                return True, "Check Passed"
        else:
            # direct compare
            for to_compare in args['match_any']:
                # check if it has specified any custom comparator
                if isinstance(to_compare, dict):
                    dict_key = list(to_compare.keys())[0]
                    if 'type' in to_compare[dict_key]:
                        # Lets hand-over this new specific comparison to comparator orchestrator
                        ret_status, ret_val = hubblestack.module_runner.comparator.run(
                            audit_id,
                            to_compare[dict_key],
                            r_compare)
                        if ret_status:
                            return True, "Check Passed"
                else:
                    # primitive datatype comparison
                    to_compare_val1 = runner_utils.apply_case_on_string(to_compare, ignore_case)
                    to_compare_val2 = runner_utils.apply_case_on_string(r_compare, ignore_case)
                    if to_compare_val1 == to_compare_val2:
                        return True, "Check Passed"

    return False, "list::match_any failure. Got={0}".format(result_to_compare)


def match_all(audit_id, result_to_compare, args):
    """
    Match all of dictionary mentioned. Match only mentioned attributes
    True if found all entry

    :param audit_id:
    :param result_to_compare:
        The value to compare.
    :param args:
        Comparator dictionary as mentioned in the check.
    """
    log.debug('Running list::match_all for check: {0}'.format(audit_id))

    ignore_case = args.get('ignore_case', False)
    for to_compare in args['match_all']:
        found_match = False
        for r_compare in result_to_compare:
            ret_status = False

            if isinstance(r_compare, dict):
                # using dict::match
                ret_status, ret_val = hubblestack.module_runner.comparator.run(
                    audit_id,
                    {"type": "dict", "match": to_compare, "ignore_case": ignore_case},
                    r_compare)
            elif isinstance(to_compare, dict):
                dict_key = list(to_compare.keys())[0]
                if 'type' in to_compare[dict_key]:
                    # Lets hand-over this new specific comparison to comparator orchestrator
                    ret_status, ret_val = hubblestack.module_runner.comparator.run(
                        audit_id,
                        to_compare[dict_key],
                        r_compare)
            else:
                # simple comparison between primitive data types
                to_compare_val1 = runner_utils.apply_case_on_string(r_compare, ignore_case)
                to_compare_val2 = runner_utils.apply_case_on_string(to_compare, ignore_case)
                ret_status = to_compare_val1 == to_compare_val2

            if ret_status:
                found_match = True
                break
        if not found_match:
            return False, "Check failed, got={0}".format(result_to_compare)
    return True, "Check Passed"


def match_any_if_keyvalue_matches(audit_id, result_to_compare, args):
    """
    We want to compare things if we found our interested key
    Even if the list does not have my interested name, it will pass

    Match dictionary elements dynamically. Match from a list of available dictionaries
    There is an argument: match_key. Match only when we found this key in result_to_compare

    True, if match_key found, and mentioned attributes matches
        , if match_key NOT found. Not even try to match anything else
    False, if match_key found and attributes do not match

    comparator:
        type: list
        match_any_if_keyvalue_matches:
            match_key: name
            args:
                - name: abc
                  running: false
                - name: xyz
                  running: false

    Input: [{name: hjk, running: false}, {name: abc, running: false}]
    Output: True, as found name: abc

    Input: [{name: hjk, running: false}, {name: abc, running: true}]
    Output: False, as found name: abc

    Input: [{name: hjk, running: false}, {name: bnm, running: false}]
    Output: True, as we didn't found the name: abc

    :param result_to_compare:
        The value to compare.
    :param args:
        Comparator dictionary as mentioned in the check.
    """
    log.debug('Running list::match_any_if_keyvalue_matches for check: {0}'.format(audit_id))

    ignore_case = args.get('ignore_case', False)
    key_name = args['match_any_if_keyvalue_matches']['match_key']
    failed_once = False
    for r_compare in result_to_compare:
        for arg_list in args['match_any_if_keyvalue_matches']['args']:
            if r_compare[key_name] == arg_list.get(key_name, None):
                ret_status, ret_val = hubblestack.module_runner.comparator.run(
                    audit_id,
                    {
                        "type": "dict",
                        "match": arg_list,
                        "ignore_case": ignore_case
                    },
                    r_compare)
            else:
                continue
            if ret_status and ret_val != "pass_as_key_not_found":
                return True, "Check Passed"
            if not ret_status:
                failed_once = True

    if failed_once:
        return False, "list::match_any_if_keyvalue_matches failure. Got={0}".format(result_to_compare)
    return True, "Check Passed"

def filter_compare(audit_id, result_to_compare, args):
    """
    A two-step comparator.
    First, filter the list
    Second, compare results

    :param result_to_compare:
        The value to compare.
    :param args:
        Comparator dictionary as mentioned in the check.
    """
    log.debug('Running list::filter_compare for check: {0}'.format(audit_id))

    filter_dict_args = args['filter_compare']['filter']
    filtered_list = []
    for r_compare in result_to_compare:
        ret_status, ret_val = hubblestack.module_runner.comparator.run(
            audit_id,
            {"type": "dict", "match": filter_dict_args},
            r_compare)
        if ret_status:
            filtered_list.append(r_compare)

    # Lets hand-over this new specific comparison to comparator orchestrator
    filter_comparator_args = {"type": "list"}
    filter_comparator_args.update(args['filter_compare']['compare'])
    return hubblestack.module_runner.comparator.run(
        audit_id,
        filter_comparator_args,
        filtered_list)

