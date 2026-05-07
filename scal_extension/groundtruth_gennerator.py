from typing import List

from DrafterBench.utils import testf
from collections import defaultdict
import string
import re

string_keys = ["font", "text_color", "text_to_be_deleted", "new_text_string", "old_text_string"]

TASK_RENDERERS = {}

IMPORT_TEMPLATE = "import testf\n"

OPEN_DOC_TEMPLATE = """doc{doc_idx} = testf.open('{filename}')
"""

EXTRACTOR_TEMPLATE = """
annoextractor{extractor_idx} = testf.extractanno(doc{doc_idx},pagenumber={vector_page}, annocolor={color_of_manually_annotated_vector!r})
"""

EXTRACTOR_OPS = {
    "annotated rectangle":
        """rectangle{oj_idx}, rfpoint{oj_idx} = annoextractor{extractor_idx}.getclip_rfpoint({page_idx}, {rect_idx})""",
    "color of manually annotated vector":
        """selected_vectors{extractor_idx} = annoextractor{extractor_idx}.anno()"""

}

TABLE_EXTRACT_TEMPLATE = """table_extractor{oj_idx} = testf.extract_table(doc=doc{doc_idx}, pagenumber={page_idx}, clip=rectangle{oj_idx})
table_data{oj_idx} = table_extractor{oj_idx}.data
"""

SELECTOR_TEMPLATE = """
selector{oj_idx} = testf.selector(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx}
)
"""

SELECTOR_FROM_TEMPLATE = """
selector{oj_idx} = testf.select_from_drawings(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    cdrawings=selected_vectors{extractor_idx}
)
"""

SELECT_DRAWINGS_MODE1_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode1_drawings_Window_Cover_Enclosure()
"""

SELECT_DRAWINGS_MODE2_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode2_drawings_Cross_Touch_Intersect()
"""

SELECT_LINES_MODE1_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode1_lines_Window_Cover_Enclosure()
"""

SELECT_LINES_MODE2_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode2_lines_Cross_Touch_Intersect()
"""

SELECT_REBARS_MODE1_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode1_rebars_Window_Cover_Enclosure()
"""

SELECT_REBARS_MODE2_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode2_rebars_Cross_Touch_Intersect()
"""

SELECT_COLUMNS_MODE1_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode1_columns_Window_Cover_Enclosure()
"""

SELECT_COLUMNS_MODE2_TEMPLATE = """
selected_vectors{ojp_idx} = selector{oj_idx}.mode2_columns_Cross_Touch_Intersect()
"""

SELECTOR_OPS = {
    ("drawings", 1): SELECT_DRAWINGS_MODE1_TEMPLATE,
    ("drawings", 2): SELECT_DRAWINGS_MODE2_TEMPLATE,

    ("lines", 1): SELECT_LINES_MODE1_TEMPLATE,
    ("lines", 2): SELECT_LINES_MODE2_TEMPLATE,

    ("rebars", 1): SELECT_REBARS_MODE1_TEMPLATE,
    ("rebars", 2): SELECT_REBARS_MODE2_TEMPLATE,

    ("columns", 1): SELECT_COLUMNS_MODE1_TEMPLATE,
    ("columns", 2): SELECT_COLUMNS_MODE2_TEMPLATE,
}


TEXT_EDIT_TEMPLATE = """
text_manipulator{oj_idx} = testf.manipulate_text(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx},
    text={text!r},
    rotate={rotate!r},
    font={font!r},
    fontsize={font_size!r},
    textcolor={text_color!r},
    align={align}
)
"""

TEXT_EDIT_OPS = {
    "get_vertical_text":
        "text_manipulator{oj_idx}.text = text_manipulator{oj_idx}.getvertext()",

    "get_horizontal_text":
        "text_manipulator{oj_idx}.text = text_manipulator{oj_idx}.gethorrtext()",

    "delete_text":
        "text_manipulator{oj_idx}.text = text_manipulator{oj_idx}.deletetext(deltex={text_to_be_deleted!r})",

    "replace_text":
        "text_manipulator{oj_idx}.text = text_manipulator{oj_idx}.replacetext(retext={old_text_string!r}, totext={new_text_string!r})",

    "finalize_text":
        "doc{doc_idx} = text_manipulator{oj_idx}.addtext()",
}

TABLE_TEMPLATE = """
table_data{oj_idx} = {data}
"""

TABLE_EDIT_TEMPLATE = """table_manipulator{oj_idx} = testf.manipulate_table(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx},
    data=table_data{oj_idx},
    arrange={arrange!r},
    font={font!r},
    fontsize={font_size!r},
    borderwidth={border_width!r},
    align={align},
)
"""

TABLE_EDIT_OPS = {
    "prun_table": "table_manipulator{oj_idx}.data = table_manipulator{oj_idx}.cuttable(delrow={rows_to_delete!r}, delcolumn={columns_to_delete!r})",

    "clean_table": "table_manipulator{oj_idx}.data = table_manipulator{oj_idx}.emptytable(startcell={cells_start_from_row_number_column_number!r}, endcell={cells_end_at_row_number_column_number!r})",

    "replace_table": "table_manipulator{oj_idx}.data = table_manipulator{oj_idx}.modifytable(repdata={new_data!r}, startcell={cells_start_from_row_number_column_number!r}, endcell={cells_end_at_row_number_column_number!r})",

    "finalize_table": "doc{doc_idx} = table_manipulator{oj_idx}.addtable()"

}

VECTOR_MANIPULATOR_TEMPLATE = """
vector_manipulator{oj_idx} = PDFbf.manipulate_draw(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    sel_drawings=selected_vectors{ojp_idx},
    fillcolor={fill_color!r},
    drwcolor={drawing_color!r},
    dashes={dashes_line_scal!r},
    closePath={closePath},
    lineJoin={lineJoin},
    lineCap={lineCap},
    width={stroke_width}
)
"""

VECTOR_REFRESH_TEMPLAE = """
doc{doc_idx} = vector_manipulator{oj_idx}.update_draw()
"""

VECTOR_ADDING_TEMPLAE = """
doc{doc_idx} = vector_manipulator{oj_idx}.add_standrawing()
"""

VECTOR_PROJECTOR_TEMPLATE = """
vector_projector{oj_idx} = PDFbf.project_draw(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx},
    sel_drawings=selected_vectors{ojp_idx},
    cdrawings=selector{oj_idx}.selected_lines,
    move={translation_x_direction_x_distance_y_direction_y_distance},
    rotation={rotation_direction_angle},
    scal={scaling_x_scaling_factor_y_scaling_factor}
)
doc{doc_idx} = vector_projector{oj_idx}.project()
"""

PROJECTOR_TEMPLATE = """
projector{oj_idx} = testf.Projector(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx},
    move={translation_x_direction_x_distance_y_direction_y_distance},
    rotation={rotation_direction_angle},
    scal={scaling_x_scaling_factor_y_scaling_factor}
)
"""

PROJECT_TEMPLATE = """
doc{doc_idx} = projector{oj_idx}.project()
"""

DELETE_DRAWING_MANIPULATOR_TEMPLATE = {
    "delete_target_vector": """
drawing_manipulator{oj_idx} = testf.draw_drawer(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    listofcdraw=selected_vectors{ojp_idx}
)
doc{doc_idx} = drawing_manipulator{oj_idx}.delete_draw()
""",

    "delete_everything": """
cleaner{oj_idx} = testf.delete(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx}
)
doc{doc_idx} = cleaner{oj_idx}.applydelete()
"""
}

REPAIRER_TEMPLATE = """
repairer{oj_idx} = testf.repairer(
    doc=doc{doc_idx},
    pagenumber={page_idx},
    clip=rectangle{oj_idx},
    cdrawings=selector{oj_idx}.selected_lines,
    sel_drawings={sel_drawings}
)
doc{doc_idx} = repairer{oj_idx}.del_repair()
"""

RECODER_TEMPLATE = """
miss_information='''file-level:{file_infor},page-level:{page_infor},order-level:{order_infor},base-level:{base_infor}'''
recorder{oj_idx} = testf.recorder(missing_information=missing_information)
recorder{oj_idx}.recording()
"""

SAVE_TEMPLATE = """
doc{doc_idx}.save('{save_name}')
"""

ALIGN_TEMPLATE = """
testf.TEXT_ALIGN_{align}
"""

linecap = {
    "sharp ends": 0,
    "semi-circle ends": 1,
    "semi-square ends": 2,
}

def check_com(value):
    if value:
        return True
    else:
        return False


def standardlize_argu(argu: str):
    return argu.replace(' ', '_').replace(',', '').replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('__', '_')


def get_template_args(tpl: str):
    formatter = string.Formatter()
    return {
        field_name
        for _, field_name, _, _ in formatter.parse(tpl)
        if field_name is not None
    }

def vector_key(vector: all ="drawings", select_mode:str=None):
    mode = 2
    if select_mode == "covered by the rectangle":
        mode = 1
    if not vector:
        vector = "drawings"
    return vector, mode


def safe_format(tpl: str, provided: dict):
    provided = {k.replace(' ', '_'): v for k, v in provided.items()}
    key_args = list(get_template_args(tpl))
    args = {k: None for k in key_args}
    args.update(provided)
    for k in list(args.keys()):
        if k in ["text_rotate_direction_angle", "data"]:
            continue
        if k not in key_args:
            args.pop(k)
    for k, v in args.items():
        if k in string_keys and v:
            args[k] = f'{v}'
        if k == "align":
            args[k] = f"testf.TEXT_ALIGN_{v.upper()}" if v else None
        if k == "arrange":
            col_pattern = re.compile(r'column width (\d*)')
            row_pattern = re.compile(r'row height (\d*)')
            if v:
                col = col_pattern.search(v)
                row = row_pattern.search(v)
                col_list = [col.group(1)] if col else None
                row_list = [row.group(1)] if row else None
                args[k] = [row_list, col_list]
        if k == "translation_x_direction_x_distance_y_direction_y_distance":
            if v:
                rf_dix = args["oj_idx"]
                x_trans = -1 * v[0][1] if v[0][0] == 'left' else v[0][1]
                y_trans = -1 * v[1][1] if v[1][0] == 'lower' else v[1][1]
                args[k] = f"[{x_trans}, {y_trans}, rfpoint{rf_dix}]"
        if k == "rotation_direction_angle":
            if v:
                rf_dix = args["oj_idx"]
                degree = -1 * v[1] if v[0] == 'counterclockwise' else v[1]
                args[k] = f"['r', {degree}, rfpoint{rf_dix}]"
        if k == "text_rotate_direction_angle":
            if v:
                degree = -1 * v[1] if v[0] == 'counterclockwise' else v[1]
                args.update({"rotate": degree})
        if k == "scaling_x_scaling_factor_y_scaling_factor":
            if v:
                rf_dix = args["oj_idx"]
                args[k] = f"['sc', [{v[0]}, {v[1]}], rfpoint{rf_dix}]"
        if k == "data":
            if v:
                args[k] = [[cell.strip() for cell in line.split(",")] for line in v.strip().splitlines()]
        if k == "lineCap":
            if v:
                args[k] = linecap.get(v)
    return tpl.format(**args)


def render_factory(task_type: str, task_space: dict):
    def render(task: list, original_task) -> str:
        combine = []
        for doc_idx, file_dict in enumerate(task):
            constant_args = {}
            constant_args.update({"doc_idx": doc_idx})
            code = []
            save_need = False
            file_infor = file_dict["filename"]
            file_com = check_com(file_infor)
            constant_args.update({"file_infor": file_infor if file_infor else "Missing"})
            constant_args.update({"filename": file_infor if file_infor else "Missing"})
            page_dict_list = list(reversed(file_dict['pages']))
            for page_idx, page_dict in enumerate(page_dict_list):
                page_infor = page_dict["page_num"]
                page_com = check_com(page_dict["page_num"])
                if page_com:
                    constant_args.update({"page_idx": page_infor - 1})
                constant_args.update({"page_infor": page_infor if page_infor else "Missing"})
                page_key = list(page_dict.keys())[1]
                if page_key == 'target annotation rectangles':
                    constant_args.update({"extractor_idx": doc_idx})
                object_dict_list = list(reversed(page_dict[page_key]))
                for rect_idx, object_dict in enumerate(object_dict_list):

                    rec_args = constant_args.copy()
                    oj_idx = str(doc_idx) + str(page_idx) + str(rect_idx)
                    if page_key != 'target annotation rectangles':
                        rec_args.update({"extractor_idx": oj_idx})
                        order_infor = object_dict["color of manually annotated vector"]
                        rect_com = check_com(object_dict["color of manually annotated vector"])
                        if rect_com:
                            rec_args.update({"color_of_manually_annotated_vector": object_dict["color of manually annotated vector"]})
                        rec_args.update({"order_infor": order_infor if order_infor else "Missing"})
                    else:
                        order_infor = object_dict["annotated rectangle"]
                        rect_com = check_com(object_dict["annotated rectangle"])
                        rec_args.update({"order_infor": order_infor if order_infor else "Missing"})
                    rec_args.update({"oj_idx": oj_idx})

                    if rect_com:
                        if page_key == 'target annotation rectangles':
                            rec_args.update({"rect_idx": object_dict["annotated rectangle"] - 1})
                        else:
                            rec_args.update({"vector_color": object_dict["color of manually annotated vector"]})

                    base_infor = []
                    if 'new format after revising' in list(object_dict.keys()):
                        fmt = object_dict['new format after revising']
                        if isinstance(fmt, dict):
                            fmt = {k.replace(' ', '_'): v for k, v in fmt.items()}
                            rec_args.update(fmt)

                    op_com = True
                    if task_type in ["revise_text", "refresh_text"]:
                        rotate = 0
                        rec_args.update({"rotate": rotate})
                    for or_op_dict in original_task[doc_idx]['pages'][-page_idx - 1][page_key][-rect_idx - 1]['operations']:
                        base_infor.append(",".join([f"{k} {v}" for k, v in or_op_dict.items()]))
                    if object_dict.get("repair requirement", None):
                        base_infor.append(f", {object_dict.get('repair requirement')}")
                    for op_dict in object_dict['operations']:
                        if task_type == "revise_text" and 'text requiring updating' in list(op_dict.keys()):
                            rotate = 90 if op_dict['text requiring updating'] == 'text in vertical' else 0
                            if rotate == 90:
                                rec_args.update({"rotate": rotate})

                        if any([True if not v else False for k, v in op_dict.items()]):
                            op_com = False

                    com_list = [file_com, page_com, rect_com, op_com]

                    if all(com_list):
                        save_need = True
                        rec_args.update({"vector_page": page_infor - 1})
                        suffix = task_space["manipulator_suffix"]
                        if "repair requirement" in list(object_dict.keys()):
                            code.append(safe_format(REPAIRER_TEMPLATE, rec_args))
                        op_dict_list = list(reversed(object_dict['operations']))
                        if task_space["manipulator_ops"]:
                            ops = task_space["manipulator_ops"]
                            if suffix:
                                code.append(safe_format(suffix, rec_args))
                            for op_idx, op_dict in enumerate(op_dict_list):
                                if "action" in list(op_dict.keys()):
                                    tpl = ops[standardlize_argu(op_dict["action"])]
                                    op_dict = {standardlize_argu(k): v for k, v in op_dict.items()}
                                    copy_const = rec_args.copy()
                                    copy_const.update(op_dict)
                                    code.append(safe_format(tpl, copy_const))
                            if task_type == "revise_text":
                                if rotate == 0:
                                    ext = TEXT_EDIT_OPS["get_horizontal_text"]
                                else:
                                    ext = TEXT_EDIT_OPS["get_vertical_text"]
                                code.append(safe_format(ext, rec_args))
                            code.append(safe_format(task_space["manipulator"], rec_args))
                        else:
                            for op_idx, op_dict in enumerate(op_dict_list):
                                ojp_idx = oj_idx + str(op_idx)
                                rec_args.update({"ojp_idx": ojp_idx})
                                op_dict = {standardlize_argu(k): v for k, v in op_dict.items()}
                                if suffix:
                                    code.append(safe_format(suffix, rec_args))
                                copy_const = rec_args.copy()
                                copy_const.update(op_dict)
                                if task_type in ["add_vector"]:
                                    vector_class = op_dict.get("vector_type_requiring_revise", None)
                                    if vector_class in ["everything", "drawing"]:
                                        copy_const.update({"ojp_idx": copy_const["extractor_idx"]})
                                if task_type == "refresh_text":
                                    if 'text_requiring_updating' in list(op_dict.keys()):
                                        rotate = 90 if op_dict['text_requiring_updating'] == 'text in vertical' else 0
                                    if rotate == 90:
                                        copy_const.update({"rotate": rotate})
                                    if rotate == 0:
                                        ext = TEXT_EDIT_OPS["get_horizontal_text"]
                                    else:
                                        ext = TEXT_EDIT_OPS["get_vertical_text"]
                                    code.append(safe_format(ext, copy_const))
                                if task_type == "delete_vector":
                                    if copy_const["vector_type_requiring_revise"] == "everything":
                                        vdt = task_space["manipulator"]["delete_everything"]
                                    else:
                                        vdt = task_space["manipulator"]["delete_target_vector"]
                                    code.append(safe_format(vdt, copy_const))
                                else:
                                    code.append(safe_format(task_space["manipulator"], copy_const))
                                preprocessor_ops = task_space["preprocessor_ops"]
                                if preprocessor_ops:
                                    if task_type in ["delete_vector", "refresh_vector", "map_vector"]:
                                        vector_class = op_dict.get("vector_type_requiring_revise", None)
                                        if vector_class != "everything":
                                            vector_class, select_mode = vector_key(vector_class, op_dict.get("mode_to_select_target_type_of_vector_for_revising", None))
                                            slt = preprocessor_ops[(vector_class, select_mode)]
                                            code.append(safe_format(slt, copy_const))
                                        else:
                                            if task_type in ["refresh_vector", "map_vector"]:
                                                vector_class = "drawings"
                                                vector_class, select_mode = vector_key(vector_class, op_dict.get("mode_to_select_target_type_of_vector_for_revising", None))
                                                slt = preprocessor_ops[(vector_class, select_mode)]
                                                code.append(safe_format(slt, copy_const))
                                            else:
                                                pass
                                    elif task_type in ["add_vector"]:
                                        vector_class = op_dict.get("vector_type_requiring_revise", None)
                                        if vector_class in ["everything", "drawing"]:
                                            pass
                                        else:
                                            vector_class, select_mode = vector_key(vector_class, op_dict.get("mode_to_select_target_type_of_vector_for_revising", None))
                                            slt = preprocessor_ops[(vector_class, select_mode)]
                                            code.append(safe_format(slt, copy_const))
                                    else:
                                        code.append(safe_format(preprocessor_ops, copy_const))
                        preprocessor = task_space["preprocessor"]
                        if preprocessor:
                            code.append(safe_format(preprocessor, rec_args))

                        if task_type != "add_vector":
                            code.append(safe_format(EXTRACTOR_OPS["annotated rectangle"], rec_args))
                        else:
                            code.append(safe_format(EXTRACTOR_OPS["color of manually annotated vector"], rec_args))
                            code.append(safe_format(EXTRACTOR_TEMPLATE, rec_args))
                    else:
                        base = ",".join(base_infor)
                        if not com_list[3]:
                            base = base + '(incomplete)'
                        rec_args.update({"base_infor": str(base) if base else "Missing"})
                        code.append(safe_format(RECODER_TEMPLATE, rec_args))

            if save_need:
                # extract_idx
                if task_type != "add_vector":
                    code.append(safe_format(EXTRACTOR_TEMPLATE, constant_args))
                saved_name = constant_args["filename"].replace('.pdf', '_updated.pdf')
                constant_args.update({"save_name": saved_name})
                code.append(safe_format(OPEN_DOC_TEMPLATE, constant_args))
                final_code = list(reversed(code))
                final_code.append(safe_format(SAVE_TEMPLATE, constant_args))
            else:
                final_code = list(reversed(code))
            combine.append("\n".join(final_code))
        return "\n".join(combine)

    return render


task_functions = {}
task_functions.update({"revise_text": {
    "preprocessor": None,
    "preprocessor_ops": None,
    "manipulator": TEXT_EDIT_TEMPLATE,
    "manipulator_ops": TEXT_EDIT_OPS,
    "manipulator_suffix": TEXT_EDIT_OPS["finalize_text"],
}})

task_functions.update({"revise_table": {
    "preprocessor": TABLE_EXTRACT_TEMPLATE,
    "preprocessor_ops": None,
    "manipulator": TABLE_EDIT_TEMPLATE,
    "manipulator_ops": TABLE_EDIT_OPS,
    "manipulator_suffix": TABLE_EDIT_OPS["finalize_table"],
}})

task_functions.update({"refresh_text": {
    "preprocessor": None,
    "preprocessor_ops": None,
    "manipulator": TEXT_EDIT_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": TEXT_EDIT_OPS["finalize_text"],
}})

task_functions.update({"refresh_table": {
    "preprocessor": TABLE_EXTRACT_TEMPLATE,
    "preprocessor_ops": None,
    "manipulator": TABLE_EDIT_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": TABLE_EDIT_OPS["finalize_table"],
}})

task_functions.update({"map_table": {
    "preprocessor": None,
    "preprocessor_ops": None,
    "manipulator": PROJECTOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": PROJECT_TEMPLATE,
}})

task_functions.update({"map_text": {
    "preprocessor": None,
    "preprocessor_ops": None,
    "manipulator": PROJECTOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": PROJECT_TEMPLATE,
}})

task_functions.update({"add_table": {
    "preprocessor": None,
    "preprocessor_ops": TABLE_TEMPLATE,
    "manipulator": TABLE_EDIT_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": TABLE_EDIT_OPS["finalize_table"],
}})

task_functions.update({"add_text": {
    "preprocessor": None,
    "preprocessor_ops": None,
    "manipulator": TEXT_EDIT_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": TEXT_EDIT_OPS["finalize_text"],
}})

task_functions.update({"delete_vector": {
    "preprocessor": SELECTOR_TEMPLATE,
    "preprocessor_ops": SELECTOR_OPS,
    "manipulator": DELETE_DRAWING_MANIPULATOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": None,
}})

task_functions.update({"refresh_vector": {
    "preprocessor": SELECTOR_TEMPLATE,
    "preprocessor_ops": SELECTOR_OPS,
    "manipulator": VECTOR_MANIPULATOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": VECTOR_REFRESH_TEMPLAE,
}})

task_functions.update({"map_vector": {
    "preprocessor": SELECTOR_TEMPLATE,
    "preprocessor_ops": SELECTOR_OPS,
    "manipulator": VECTOR_PROJECTOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": None,
}})

task_functions.update({"add_vector": {
    "preprocessor": SELECTOR_FROM_TEMPLATE,
    "preprocessor_ops": SELECTOR_OPS,
    "manipulator": VECTOR_MANIPULATOR_TEMPLATE,
    "manipulator_ops": None,
    "manipulator_suffix": VECTOR_ADDING_TEMPLAE,
}})

def generate_code(json_data, original_data):
    code = []
    code.append(IMPORT_TEMPLATE)
    task_type = json_data["Tasktype"]
    render = render_factory(task_type, task_functions[task_type])
    # renderer = TASK_RENDERERS[task_type]
    entry = json_data["Information"]
    original_entry = original_data["Information"]
    code.append(render(entry, original_entry))
    return "\n".join(code)










