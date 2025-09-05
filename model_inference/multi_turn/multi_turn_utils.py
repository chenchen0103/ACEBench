
import importlib
import inspect
import json
import re
import copy
from typing import List

CLASS_FILE_PATH_MAPPING_ZH = {
    "BaseApi": "model_inference.multi_turn.scenarioszh.phone_platform.base_api",
    "MessageApi": "model_inference.multi_turn.scenarioszh.phone_platform.message",
    "ReminderApi": "model_inference.multi_turn.scenarioszh.phone_platform.reminder",
    "FoodPlatform": "model_inference.multi_turn.scenarioszh.phone_platform.food_services",
    "Travel": "model_inference.multi_turn.scenarioszh.travel",
}

CLASS_FILE_PATH_MAPPING_EN = {
    "BaseApi": "model_inference.multi_turn.scenariosen.phone_platform.base_api",
    "MessageApi": "model_inference.multi_turn.scenariosen.phone_platform.message",
    "ReminderApi": "model_inference.multi_turn.scenariosen.phone_platform.reminder",
    "FoodPlatform": "model_inference.multi_turn.scenariosen.phone_platform.food_services",
    "Travel": "model_inference.multi_turn.scenariosen.travel",
}
STATELESS_CLASSES = []

def execute_agent_func_call(
    func_call_list: list[str],  # a list of strings of func calls
    initial_config: dict,
    involved_classes: list,
    model_name: str,
    test_entry_id: str,
    language: str
) -> tuple[list[str], dict]:
    """
    TODO: Add docstring
    """
    class_method_name_mapping = {}
    involved_instances = {}
    for class_name in involved_classes:
        if language == "zh":
            module_name = CLASS_FILE_PATH_MAPPING_ZH[class_name]
        elif language == "en":
            module_name = CLASS_FILE_PATH_MAPPING_EN[class_name]
        # TODO: Handler the model name issue from handler more elegantly
        instance_name = (
            f"{model_name.replace('-', '_').replace('.', '_').replace('/', '_')}_{test_entry_id}_{class_name.lower()}_instance"
        )
        if instance_name not in globals():
            module = importlib.import_module(module_name)
            class_ = getattr(module, class_name)
            class_instance = class_()
            if class_name not in STATELESS_CLASSES:
                class_initial_config = initial_config.get(class_name, {})
                # Deep copy the initial configuration to avoid mutation issues
                class_instance._load_scenario(
                    copy.deepcopy(class_initial_config), long_context=False
                )
                class_initial_baseconfig = initial_config.get("BaseApi", {})
                # Deep copy the initial configuration to avoid mutation issues
                class_instance._load_scenario(
                    copy.deepcopy(class_initial_baseconfig), long_context=False
                )
            globals()[instance_name] = class_instance
        # This happens in subsequent turns
        else:
            class_instance = globals()[instance_name]

        involved_instances[class_name] = class_instance

        # Retrieve all method names and map them to the instance
        for method_name, method in inspect.getmembers(
            class_instance, predicate=inspect.ismethod
        ):
            # Skip private methods
            if method_name.startswith("_"):
                continue
            if method_name in class_method_name_mapping:
                class_method_name_mapping[method_name].append(instance_name)  # 直接在原列表上追加
            else:
                class_method_name_mapping[method_name] = [instance_name]  # 创建新的列表


    execution_results = []
    for func_call in func_call_list:
        # Add the instance name to the method calls
        func_calls = _process_method_calls(func_call, class_method_name_mapping)
        
        try:
            for func_call in func_calls:
                func_call_result = eval(func_call)
            execution_results.append(func_call_result)
        except Exception as e:
            errors = f"Error during execution: {str(e)}"
            return errors, involved_classes

    for index in range(len(execution_results)):
        if type(execution_results[index]) == str:
            continue
        elif type(execution_results[index]) == dict:
            # Some function returns a object instance, which is not serializable
            try:
                execution_results[index] = json.dumps(execution_results[index])
            except:
                execution_results[index] = str(execution_results[index])
        else:
            execution_results[index] = str(execution_results[index])

    return execution_results, involved_instances


def is_empty_execute_response(input_list: list):
    if len(input_list) == 0:
        return True
    if len(input_list) == 1 and len(input_list[0]) == 0:
        return True
    return False


import re

def _process_method_calls(function_call_string: str, instance_mapping) -> List[str]:
    
    # 1. Compile regular expression
    compiled_pattern = re.compile(r"\b([a-zA-Z_]\w*)\s*(?=\()")

    # 2. Find the first match
    match = compiled_pattern.search(function_call_string)

    # 3. Process the match
    processed_string_list = []
    if match:
        # Get the start and end positions of the match
        match_start, match_end = match.span()

        # Concatenate the strings before and after the match
        before_match = function_call_string[:match_start]
        after_match = function_call_string[match_end:]

        # Process the matched function name using replace_function
        func_name = match.group(1)
        if func_name in instance_mapping:
            for name in instance_mapping[func_name]:
                func_names = f"{name}.{func_name}"
                # Concatenate the final string
                processed_string = before_match + func_names + after_match
                processed_string_list.append(processed_string)
    return processed_string_list
