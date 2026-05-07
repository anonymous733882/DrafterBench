from __future__ import annotations

import os
import pickle
import sys
try:
    import lmdb
except ImportError:
    lmdb = None
from pathlib import Path

sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../.."))
import json
import random
import secrets
from dataclasses import dataclass
from DrafterBench.utils.testf.functions import fontlist
import copy
from DrafterBench.methods import task_sets
from tqdm import tqdm
from DrafterBench.scal_extension.groundtruth_gennerator import generate_code

MODULE_DIR = Path(__file__).resolve().parent
LMDB_PATH = MODULE_DIR / "task_component.lmdb"

word_list = [
    "beam",
    "column",
    "slab",
    "footing",
    "girder",
    "rebar",
    "concrete",
    "steel",
    "joint",
    "section",
    "elevation",
    "foundation",
]

colors = [
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "black",
    "gray",
    "cyan",
    "magenta",
]
direction = [None, "clockwise", "counterclockwise"]
align = ["left", "right", "center", "justify"]
vague_list = ["suitable", "common", "general", "professional", "appropriate"]
annotated_vectors = ["columns", "rebars", "lines", "drawings", "everything"]
select_mode = ["covered by the rectangle", "intersected by the rectangle"]
x_direction = ["right", "left"]
y_direction = ["upper", "lower"]
magnitude = ["a little", "some", "a bit"]
degree = ["larger", "smaller"]
text_direction = ["text in horizontal", "text in vertical"]
lineJoint = ["sharp join", "rounded join", "cut-off join"]
lineCap = ["sharp ends", "semi-circle ends", "semi-square ends"]
map_keys = ["translation [(x direction, x distance), (y direction, y distance)]",
                "rotation [direction, angle]",
                "scaling [x scaling factor, y scaling factor]",
                "text rotate [direction, angle]"
            ]

DEFAULT_MODEL = "google/gemma-3-27b-it"
DEFAULT_PROVIDER = "deepinfra"


@dataclass
class GenerationConfig:
    model: str = DEFAULT_MODEL
    provider: str | None = DEFAULT_PROVIDER
    temperature: float = 0.7
    max_completion_tokens: int = 2000


_generation_config = GenerationConfig()


def get_generation_config():
    return copy.deepcopy(_generation_config)


def configure_generation(
    model: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
):
    global _generation_config
    if model is not None:
        _generation_config.model = model
    if provider is not None:
        _generation_config.provider = provider
    if temperature is not None:
        _generation_config.temperature = temperature
    if max_completion_tokens is not None:
        _generation_config.max_completion_tokens = max_completion_tokens
    return get_generation_config()


def _model_id(config: GenerationConfig):
    return f"{config.provider}/{config.model}" if config.provider else config.model


def _apply_generation_overrides(
    model: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
):
    previous = get_generation_config()
    configure_generation(model, provider, temperature, max_completion_tokens)
    return previous


def openfile(file):
    f = open(file, 'r', encoding='utf-8')
    content = json.load(f)
    return content


def get_random_word():
    random_word = secrets.choice(word_list)
    return random_word


def generate_sentence(length=10):
    sentence = ""
    for i in range(length):
        sentence += get_random_word() + " "
    sentence = sentence.capitalize()
    sentence = sentence[:-1] + "."
    return sentence


def generate_natural_sentence(length=10):
    prompt = """
    You are a text generator specialized in civil engineering and construction documentation.

Task:
Generate one random civil engineering–related sentence or short instruction.

Rules:
1. The content must be related to civil engineering or construction practice.
2. The sentence may describe an instruction, requirement, note, or action.
3. Use realistic but fictional details (materials, dimensions, elements, or processes).
4. Keep the sentence self-contained and understandable on its own.
5. Do not reference any external documents, drawings, or standards.
6. Do not include explanations, bullet points, or additional commentary.

Output:
A single civil engineering–related sentence or short instruction.
    """
    sentence = get_response(prompt)
    return sentence


def get_response(
    prompt,
    model: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
):
    from litellm import completion
    config = get_generation_config()
    if model is not None:
        config.model = model
    if provider is not None:
        config.provider = provider
    if temperature is not None:
        config.temperature = temperature
    if max_completion_tokens is not None:
        config.max_completion_tokens = max_completion_tokens

    messages = [
        {
            "role": "system",
            "content": (
                "You may reason internally, but do not reveal your reasoning. "
                "Only output the final answer. "
                "Do not include <think> tags."
            )
        },
        {"role": "user", "content": prompt}
    ]
    res = completion(
        model=_model_id(config),
        messages=messages,
        temperature=config.temperature,
        max_completion_tokens=config.max_completion_tokens,
    )
    response = res.choices[0].message.content
    return response


def load_task_template(tasktype: str):
    json_path = MODULE_DIR / f"{tasktype}_elements.json"
    if lmdb is not None and LMDB_PATH.exists():
        env = lmdb.open(str(LMDB_PATH), readonly=True, lock=False)
        txn = env.begin()
        task_byte = txn.get(tasktype.encode("utf-8"))
        env.close()
        if task_byte is not None:
            return pickle.loads(task_byte)
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def savedate(data, jsonpath):
    with open(jsonpath, 'w', encoding='utf-8') as w:
        json.dump(data, w, ensure_ascii=False, indent=4)


def civil_table(row_num, col_num):
    prompt = f"""
    You are a table generator for civil engineering documentation.

Task:
Generate a random but realistic civil engineering–related table based on the description below.

Rules:
1. The table must have exactly the number of rows and columns specified in the description.
2. The first row must always be a header row.
3. The remaining rows must contain plausible, domain-appropriate values used in civil engineering practice.
4. Use standard civil engineering terminology (e.g., foundations, slabs, beams, columns, materials, dimensions, reinforcement).
5. All values should be fictional but technically reasonable.
6. Do not add extra rows, columns, explanations, or commentary.
7. Output the table in plain text using rows separated by new lines and columns separated by commas.
8. Always write new tables instead of copying the example.

Description:
Generate a table with {row_num} rows and {col_num} columns.

An example illustration for a table with 2 rows and 3 columns:
"First row content for three columns"; 
"Second row content three columns"

Output:
The generated table only.
    """
    table = get_response(prompt)
    return table


def random_value(paramater, vague=None):
    if paramater == "filename":
        random_word = secrets.choice(word_list)
        return random_word + ".pdf"
    if paramater == "pages":
        return random.randint(1, 20)
    if paramater == "annotated rectangle":
        return random.randint(1, 20)
    if paramater == "color of manually annotated vector":
        return secrets.choice(colors)
    if paramater == "vector type requiring revise":
        return secrets.choice(annotated_vectors)
    if paramater in ["text", "new text string", "old text string"]:
        sentence = generate_natural_sentence()
        return sentence
    if paramater == "text to be deleted":
        words = get_random_word()
        return words
    if paramater == "font":
        return secrets.choice(fontlist)
    if paramater == "font size":
        return random.randint(1, 30)
    if paramater == "stroke width":
        return random.randint(1, 30)
    if paramater == "border width":
        return random.randint(1, 5)
    if paramater == "drawing color":
        return secrets.choice(colors)
    if paramater == "text requiring updating":
        return secrets.choice(text_direction)
    if paramater == "text color":
        return secrets.choice(colors)
    if paramater == "fill color":
        return secrets.choice(colors)
    if paramater == "vector select mode":
        return secrets.choice(select_mode)
    if paramater == "dashes line scal":
        return str([random.randint(1, 5), random.randint(1, 5)]) + str(random.randint(1, 5))
    if paramater == "closePath":
        return secrets.choice(["True", "False"])
    if paramater == "lineJoin":
        return secrets.choice(["True", "False"])
    if paramater == "lineCap":
        return secrets.choice(lineCap)
    if paramater == "mode to select target type of vector for revising":
        return secrets.choice(select_mode)
    if paramater == "cells start from [row number, column number]":
        return [random.randint(1,7), random.randint(1,7)]
    if paramater == "cells end at [row number, column number]":
        return [random.randint(1,7), random.randint(1,7)]
    if paramater == "rows to delete":
        start_row = random.randint(1,7)
        rows_num = random.randint(1,7) - 1
        if rows_num:
            return list(range(start_row, start_row + rows_num + 1))
        else:
            return [start_row]
    if paramater == "columns to delete":
        start_column = random.randint(1,7)
        columns_num = random.randint(1,7) - 1
        if columns_num:
            return list(range(start_column, start_column + columns_num + 1))
        else:
            return [start_column]
    if paramater == "columns to delete":
        return [random.randint(1,7), random.randint(1,7)]
    if paramater == "text rotate [direction, angle]":
        if vague:
            return secrets.choice(direction), secrets.choice(magnitude)
        else:
            return secrets.choice(direction), random.randint(1, 180)
    if paramater == "translation [(x direction, x distance), (y direction, y distance)]":
        if vague:
            return [(secrets.choice(x_direction), secrets.choice(magnitude)), (secrets.choice(y_direction), secrets.choice(magnitude))]
        else:
            return [(secrets.choice(x_direction), random.randint(1, 50)), (secrets.choice(y_direction), random.randint(1, 50))]
    if paramater == "rotation [direction, angle]":
        if vague:
            return secrets.choice(direction), secrets.choice(magnitude)
        else:
            return secrets.choice(direction), random.randint(1, 180)
    if paramater == "scaling [x scaling factor, y scaling factor]":
        if vague:
            return secrets.choice(degree), secrets.choice(degree)
        else:
            return round(random.uniform(1, 3), 1), round(random.uniform(1, 3), 1)
    if paramater == "align":
        return secrets.choice(align)
    if paramater == "data":
        return civil_table(random.randint(2, 6), random.randint(2, 6))
    if paramater == "new data":
        return civil_table(random.randint(2, 6), random.randint(2, 6))
    if paramater == "arrange":
        arrange = ""
        column, row = [random.randint(0, 1), random.randint(0, 1)]
        column_width = f"column width {random.randint(20, 100)}"
        row_height = f"row height {random.randint(20, 100)}"
        if column:
            arrange += column_width
            "and".join([arrange, row_height])
        else:
            arrange += row_height
        return arrange


def instruction_checker(task_json, instruction):
    structured_prompt = f"""
        You are a checker. A data-to-text generator convert the following JSON into a natural-language instruction
    that a user would say as a drawing revision guidance for the target annotated position. Make it short, clear, action-oriented, and human-like.
    PLease supply the current instruction to make sure it not missing any arguments with meaningful value. 

    List of JSON hierarchical dictionaries:
    {task_json}

    Output from the generator:
    {instruction}

    Follow the following styles:
    - imperative tone
    - short and precise
    - avoid technical jargon unless needed
    - mention target classes explicitly
    - Only include arguments whose values are NOT None.
    - Completely omit any argument whose value is None — do not mention it directly or indirectly.
    - Do not invent default values. If a value is None, treat the argument as nonexistent.
    - Do not miss any arguments whose values are present.
    - Contain all information in the list of JSON hierarchical dictionaries


    Output:
    The instruction full fill the requirements only. No any comments or explanation.
    """

    checked_instruction = get_response(structured_prompt)
    return checked_instruction


def convert_to_instruction(new_task):
    task_json = new_task["Information"]

    if new_task["Tasktype"] == "add_vector":
        prefix = """
Engineers manually drew temporary vector lines in multiple colors. They attempted to add target classes from the temporary vector lines with specific annotation colors to the standard drawings and assign them the required properties. The above information is provided by a list of JSON hierarchical dictionaries. Convert the following list of JSON hierarchical dictionaries into a natural-language instruction
that would serve as the detailed guidance for drawing revision tasks. Make it clear, precise, detailed and human-like to clearly indicate the annotated drawing color and all noted details of each operation.
"""
        mid = """
(including the annotated drawing color, if specificed)
"""
    else:
        prefix = """
The engineer marked the locations requiring modification with rectangles on the drawings and prepared one or more modification operations for the corresponding positions. The above information is provided by a list of JSON hierarchical dictionaries. Convert the following list of JSON hierarchical dictionaries into a natural-language instruction
that would serve as the detailed guidance for drawing revision tasks. Make it clear, precise, detailed and human-like to clearly indicate the annotation rectangle and all noted details of each operation.
"""
        mid = """
(including the sequence of the annotated rectangles, if specificed)
"""

    structured_prompt = f"""
You are a data-to-text generator. {prefix} 

List of JSON hierarchical dictionaries:
{task_json}

Follow the style:
- imperative tone
- short and precise
- avoid technical jargon unless needed
- mention target classes explicitly
- Only include arguments whose values are NOT null.
- Completely omit any argument whose value is null — do not mention it directly or indirectly.
- Preserve all arguments whose values is not "null".
- Do not invent default values or ask placeholders. If a value is null, treat the argument as nonexistent, skip and don't mention it.
- Ensure the detailed values {mid} of all existent arguments whose values are present are presented explicitly in the instruction.
- Contain all information in the list of JSON hierarchical dictionaries
- Take the exact value of each argument. Do not supplement, assume, or placeholder any arguments with null values. Phrase naturally.


Output:
Only the instruction directly.  No any comments or explanation.

    """

    structured_instruct = get_response(structured_prompt)
    # checked_str_instruction = instruction_checker(task_json, structured_instruct)

    unstructured_prompt = f"""
        You are a data-to-text generator. Rewrite the following drawing revision instruction to a style that is the deliberate opposite of typical engineering-review instructions.
    
    List of JSON hierarchical dictionaries:
    {task_json}
    
    Instruction:
    {structured_instruct}

    Follow these style requirements:

    - Avoid concise, imperative phrasing.
    - Avoid direct engineering terminology (e.g., “delete,” “clip region,” “target class”).
    - Speak indirectly.
    - Add several softening phrases (“it might be nice if…”, “I was thinking…”, “maybe you could consider…”).
    - Only include arguments whose values are NOT null.
    - Completely omit any argument whose value is null — do not mention it directly or indirectly.
    - Do not invent default values or ask placeholders. If a value is null, treat the argument as nonexistent.
    - Preserve all arguments whose values are present.
    - Ensure the detailed values of all existent arguments whose values are present are presented explicitly in the instruction.
    - Contain all information in the list of JSON hierarchical dictionaries
    - The instruction must still express the same underlying intent, just in an obfuscated, indirect, and verbose manner.

    
    Output:
    Only the revised instruction directly. No any comments or explanation.

    """

    unstructured_instruct = get_response(unstructured_prompt)

    return structured_instruct, unstructured_instruct


def count_argu(task_dict: dict, argue_type: str):
    argu = []
    if argue_type in list(task_dict.keys()):
        argu.extend(task_dict[argue_type])

    for op in task_dict["operations"]:
        if argue_type in list(op.keys()):
            argu.extend(op[argue_type])
    return argu


class Random_setter(object):
    def __init__(self, target_num):
        self.target_num = target_num
        self.set = False

    def random_set(self):
        if self.target_num > 0:
            value = random.randint(0, 1)
            if value:
                self.set = True
                self.target_num -= 1
            else:
                self.set = False
        return self.set


def task_generator(task: dict, meta: list):
    global annotated_vectors
    nece_argu = count_argu(task, "necessary_arguments")
    vague_argu = count_argu(task, "vaguly_defined_arguments")

    markup = "target vector" if task["tasktype"] == "add_vector" else "target annotation rectangles"

    tamp = {
        "files": 1,
        "pages": 1,
        markup: 1,
        "operations": 1,
    }
    if meta[0]:
        max_num = 3
        object_keys = ["files", "pages", markup]
        if max_num > 1:
            tamp["files"] = random.randint(1, max_num)
            max_num -= (tamp["files"] - 1)
        if max_num > 1:
            tamp["pages"] = random.randint(1, max_num)
            max_num -= (tamp["pages"] - 1)
        if max_num > 1:
            tamp[markup] = random.randint(1, max_num)
            max_num -= (tamp[markup] - 1)
        check_list = [True if tamp[x] > 1 else False for x in object_keys]
        if not any(check_list):
            check_int = random.randint(0, 2)
            tamp[object_keys[check_int]] = random.randint(2, 3)

    if meta[1]:
        tamp.update({"operations": random.randint(2, 3)})

    new_task = {
        "Tasktype": task["tasktype"],
        "Single|Multiple_objects": "Multiple_Object" if meta[0] else "Single_Object",
        "Single|Multiple_operations": "Multiple_Operation" if meta[1] else "Single_Operation",
        "Complete|Incomplete": "Error" if meta[2] and nece_argu else "Complete",
        "Precise|Vague": "Vague" if meta[3] and vague_argu else "Precise",
        "Information": [],
    }



    if new_task["Complete|Incomplete"] == "Error":
        error_num = random.randint(1, len(nece_argu))
    else:
        error_num = 0
    error_setter = Random_setter(error_num)
    if new_task["Precise|Vague"] == "Vague":
        vague_num = random.randint(1, len(vague_argu))
    else:
        vague_num = 0
    vague_setter = Random_setter(vague_num)

    for file_sq in range(tamp["files"]):
        new_file = {
            "filename": None if error_setter.random_set() and (file_sq == 0) else random_value("filename"),
            "pages": []
        }
        for page_sq in range(tamp["pages"]):
            new_page = {
                "page_num": None if error_setter.random_set() and (page_sq == 0) and new_file["filename"] else random_value("pages"),
                markup: []
            }
            for object_sq in range(tamp[markup]):
                object_name = task["necessary_arguments"][2]
                new_object = {
                    object_name: None if error_setter.random_set() and (object_sq == 0) and new_page["page_num"] else random_value(object_name),
                    "operations": []
                }
                if task["tasktype"] in ["revise_text"]:
                    tex_direction_int = random.randint(0,1)
                    if tex_direction_int:
                        new_object["operations"].append({"text requiring updating": random_value("text requiring updating")})
                for operations_sq in range(tamp["operations"]):
                    operation_dict = random.choice(task["operations"])
                    new_operation = {
                        "action": operation_dict["action"],
                    }
                    for nece_para in operation_dict["necessary_arguments"]:

                        new_operation.update({nece_para: None if error_setter.random_set() else random_value(nece_para)})
                    pair = False
                    if task["tasktype"] in ["map_table", "map_text", "map_vector"]:
                        optional_index = random.randint(0, 2)
                        new_operation.update({operation_dict["optional_arguments"][optional_index]: random_value(operation_dict["optional_arguments"][optional_index])})
                    for op_para in operation_dict["optional_arguments"]:
                        optional_index = random.randint(0, 1)
                        if task["tasktype"] == "delete_vector":
                            if new_operation["vector type requiring revise"] == "everything":
                                optional_index = 0
                        if op_para == 'cells start from [row number, column number]' and optional_index:
                            pair = True
                        if optional_index and op_para != 'cells end at [row number, column number]':
                            new_operation.update({op_para: random_value(op_para)})
                        if pair and op_para == 'cells end at [row number, column number]':
                            new_operation.update({op_para: random_value(op_para)})


                    if operation_dict["vaguly_defined_arguments"] and new_task["Precise|Vague"] == "Vague":
                        check_list = [True if key in operation_dict["vaguly_defined_arguments"] else False for key in list(new_operation.keys())]
                        if not any(check_list):
                            vague_num2 = random.randint(1, len(operation_dict["vaguly_defined_arguments"]))
                            vague_para = random.sample(operation_dict["vaguly_defined_arguments"], vague_num2)
                            for v, va_para in enumerate(vague_para):
                                if v == 0 or (vague_setter.target_num == vague_num):
                                    if va_para in map_keys:
                                        new_operation.update({va_para: random_value(va_para,True)})
                                    else:
                                        new_operation.update({va_para: random.choice(vague_list)})
                                    vague_setter.target_num -= 1
                                else:
                                    if va_para in map_keys:
                                        new_operation.update({va_para: random_value(va_para,True) if vague_setter.random_set() else random_value(va_para)})
                                    else:
                                        new_operation.update({va_para: random.choice(vague_list) if vague_setter.random_set() else random_value(va_para)})
                        else:
                            for key in list(new_operation.keys()):
                                if key in operation_dict["vaguly_defined_arguments"]:
                                    if vague_setter.target_num == vague_num or vague_setter.random_set():
                                        if key in map_keys:
                                            new_operation.update({key: random_value(key, True)})
                                        else:
                                            new_operation.update({key: random.choice(vague_list)})
                                        vague_setter.target_num -= 1
                            pass

                    new_object["operations"].append(new_operation)
                if task["tasktype"] == "delete_vector":
                    # repair_index = 1
                    repair_index = random.randint(0,1)
                    if repair_index:
                        new_object.update({"repair requirement": "repair the drawings after this deleting"})
                if task["tasktype"] in ["revise_table", "revise_text"]:
                    new_object.update({"new format after revising": {}})

                    for op_para in task["optional_arguments"]:
                        optional_index = random.randint(0, 1)
                        if optional_index:
                            if op_para == "text requiring updating":
                                new_object.update({"text requiring updating": random_value(op_para)})
                            else:
                                new_object["new format after revising"].update({op_para: random_value(op_para)})
                    if task["vaguly_defined_arguments"] and new_task["Precise|Vague"] == "Vague":
                        check_list = [True if key in task["vaguly_defined_arguments"] else False for key in list(new_object["new format after revising"].keys())]
                        if not any(check_list):
                            vague_num = random.randint(1, len(task["vaguly_defined_arguments"]))
                            vague_para = random.sample(task["vaguly_defined_arguments"], vague_num)
                            for v, va_para in enumerate(vague_para):
                                if v == len(vague_para) and (vague_setter.target_num == len(vague_argu)):
                                    if va_para in map_keys:
                                        new_object["new format after revising"].update({va_para: random_value(va_para,True)})
                                    else:
                                        new_object["new format after revising"].update({va_para: random.choice(vague_list)})
                                    vague_setter.target_num -= 1
                                else:
                                    if va_para in map_keys:
                                        new_object["new format after revising"].update({va_para: random_value(va_para,True) if vague_setter.random_set() else random_value(va_para)})
                                    else:
                                        new_object["new format after revising"].update({va_para: random.choice(vague_list) if vague_setter.random_set() else random_value(va_para)})
                        else:
                            for key in list(new_object["new format after revising"].keys()):
                                if key in task["vaguly_defined_arguments"]:
                                    if vague_setter.target_num == len(vague_argu) or vague_setter.random_set():
                                        if key in map_keys:
                                            new_object["new format after revising"][key] = random_value(key, True)
                                        else:
                                            new_object["new format after revising"][key] = random.choice(vague_list)
                            pass

                new_page[markup].append(new_object)
                annotated_vectors = ["columns", "rebars", "lines", "drawings", "everything"]
            new_file["pages"].append(new_page)
        new_task["Information"].append(new_file)

        if error_setter.target_num and (error_setter.target_num == len(nece_argu)):
            # random_nece = random.choice(task["necessary_arguments"])
            new_task["Information"][0]["filename"] = None

    return new_task


def vague_filter(task:list):
    vague_value = vague_list + magnitude + degree
    for f_idx, file_dict in enumerate(task):
        for p_idx, page_dict in enumerate(file_dict['pages']):
            page_keys = list(page_dict.keys())
            for o_idx, ob_dict in enumerate(page_dict[page_keys[1]]):
                for op_idx, op in enumerate(ob_dict['operations']):
                    for k, v in op.items():
                        if k == map_keys[0]:
                            if v[0][1] or v[1][1] in vague_value:
                                task[f_idx]['pages'][p_idx][page_keys[1]][o_idx]['operations'][op_idx][k] = random_value(k)
                        elif k == map_keys[1]:
                            if v[1] in vague_value:
                                task[f_idx]['pages'][p_idx][page_keys[1]][o_idx]['operations'][op_idx][k] = random_value(k)
                        elif k == map_keys[2]:
                            if v[0] or v[1] in vague_value:
                                task[f_idx]['pages'][p_idx][page_keys[1]][o_idx]['operations'][op_idx][k] = random_value(k)
                        else:
                            if v in vague_value:
                                task[f_idx]['pages'][p_idx][page_keys[1]][o_idx]['operations'][op_idx][k] = random_value(k)
                if 'new format after revising' in list(ob_dict.keys()):
                    for m, n in ob_dict['new format after revising'].items():
                        if n in vague_value:
                            pages = task[f_idx]['pages']
                            objects = pages[p_idx][page_keys[1]]
                            format = objects[o_idx]['new format after revising']
                            format[m] = random_value(m)
    return task

def get_tasks(task: dict, nece_argu: list, vague_argu: list, multi_op: bool):
    task_sink = []
    # single_task
    meta_list = [[(i >> bit) & 1 for bit in range(3, -1, -1)] for i in range(16)]

    for meta in tqdm(meta_list):
        if not meta[0]:
            continue

        if not multi_op:
            meta[1] = 0
        new_task = task_generator(task, meta)
        task_information = copy.deepcopy(new_task["Information"])
        task_for_code = copy.deepcopy(new_task)
        if new_task["Precise|Vague"] == "Vague":
            vague_filtered = vague_filter(task_information)
            task_for_code.update({"Information":vague_filtered})
        ground_truth = generate_code(task_for_code, new_task)
        new_task.update({"Groundtruth": ground_truth})
        # codes = get_ground_truth(new_task)
        structured, unstructured = convert_to_instruction(new_task)
        structured_task = copy.deepcopy(new_task)
        structured_task.update({"Structured/Unstructured": "Structured"})
        structured_task.update({"Instruction": structured})
        unstructured_task = copy.deepcopy(new_task)
        unstructured_task.update({"Structured/Unstructured": "Unstructured"})
        unstructured_task.update({"Instruction": unstructured})
        task_sink.extend([structured_task, unstructured_task])
    return task_sink


def scalup(
    scal_num: int,
    model: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
):
    previous = _apply_generation_overrides(
        model=model,
        provider=provider,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
    )
    try:
        new_tasks = []
        for task in task_sets:
            task_com = load_task_template(task)
            nece_argu = count_argu(task_com, "necessary_arguments")
            vague_argu = count_argu(task_com, "vaguly_defined_arguments")
            multi_op = any(op["recallable"] == "True" for op in task_com["operations"])
            tasks = get_tasks(task_com, nece_argu, vague_argu, multi_op)
            new_tasks.extend(tasks[:scal_num])
        return new_tasks
    finally:
        configure_generation(
            model=previous.model,
            provider=previous.provider,
            temperature=previous.temperature,
            max_completion_tokens=previous.max_completion_tokens,
        )


def generate_extension_file(
    output_path: str,
    scal_num: int = 1,
    model: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    max_completion_tokens: int | None = None,
):
    new_tasks = scalup(
        scal_num,
        model=model,
        provider=provider,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
    )
    savedate(new_tasks, output_path)
    return new_tasks
