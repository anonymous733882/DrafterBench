import copy
import re

from collections import defaultdict

def describe_selection(sel_drawings):
    """
    Convert selector output metadata to human-readable content description.
    """
    if not sel_drawings:
        return "unknown content"
    full_name = ''
    for entry in sel_drawings:
        name = entry.get("data_name", "drawings")
        full_name = full_name + name

    entry = sel_drawings[0]
    pos_args = entry.get("position_arguments", [])
    clip = None
    for k, v in pos_args:
        if k == "clip":
            clip = v[0]

    if clip:
        return f"{full_name} selected from the {clip.split('-')[-1]} annotation"

    return f"{full_name} selected"

def extract_tool_arguments(tool_call):
    """
    Convert tool_call.arguments_value to a clean dict.
    """
    return {
        k: v[0]
        for k, v in tool_call.get("arguments_value", [])
        if v[1]  # only include confirmed arguments
    }

def describe_table(data):
    """
    Create a lightweight semantic description of a table.
    """
    if not data:
        return "table"

    rows = len(data)
    cols = len(data[0]) if data[0] else 0
    return f"table with {rows} rows and {cols} columns"


def get_final_filename(chain):
    if "save" in list(chain.keys()):
        if chain["save"]:
            return chain["save"][0]["save_path"][0]
    return None

def handle_drawing_manipulator(op, page_map):
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    # ---- determine operation type ----
    tool_calls = op.get("tool_callings", [])
    is_refresh = any(
        tc["tool_name"] == "update_drawings"
        for tc in tool_calls
    )

    action_label = "refreshed" if is_refresh else "added"

    # targets = []
    sel_drawings = args.get("sel_drawings")[0]
    # if sel_drawings and sel_drawings[1]:
    #     for item in sel_drawings[0]:
    #         targets.append(item["data_name"])
    # sel_drawings = args["sel_drawings"][0]
    content_desc = describe_selection(sel_drawings)

    content = f"{content_desc} {action_label}"

    position = dict(sel_drawings[0].get('position_arguments'))

    clip = position.get('clip')[0].split('-')[-1]

    fmt = {}
    for k in ("fillcolor",
        "drwcolor",
        "dashes",
        "closePath",
        "lineJoin",
        "lineCap",
        "width",):
        if k in args and args[k][1]:
            fmt[k] = args[k][0]

    page_map[page].append({
        "content": content,
        'vector': sel_drawings[0],
        "format": fmt,
        "clip": clip
    })

def handle_delete_selected_vectors(op, page_map):
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    listofdraw = args["listofdraw"][0]

    # Describe what was deleted
    if listofdraw:
        for item in listofdraw:

            content_desc = f"deleted {item.get('data_name', 'drawings')}"
            entry = {}
            position = dict(item.get('position_arguments'))

            clip = position.get('clip')
            if clip[1]:
                a = clip[0].split('-')
                pos = clip[0].split('-')[-1]
                content_desc = content_desc + f" in clip {pos}"
                entry.update({"clip": pos})

            entry.update({"content": content_desc,
                          "vector": item if item else None
                          })


            page_map[page].append(copy.deepcopy(entry))

def handle_projector(op, page_map):
    """
    Handle table mapping (projector) operations.
    """
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    transform = {}

    # move
    if "move" in args and args["move"][1][1]:
        translation = args["move"][0]
        translation[2] = translation[2].split('-')[-1]
        transform["move"] = translation

    if "rotation" in args and args["rotation"][1][1]:
        rotation = args["rotation"][0]
        rotation[2] = rotation[2].split('-')[-1]
        transform["rotation"] = rotation

    if "scal" in args and args["scal"][1][1]:
        scal = args["scal"][0]
        scal[2] = scal[2].split('-')[-1]
        transform["scal"] = scal

    entry = {
        "transform": transform
    }

    clip = args.get("clip")

    content = "area mapped"
    if clip[1]:
        pos = clip[0].split('-')[-1]
        content = content + f" in clip {pos}"
        entry.update({"clip": pos})

    entry.update({"content": content})

    page_map[page].append(entry)

def handle_draw_projector(op, page_map):
    """
    Handle vector mapping (draw_projector).
    """
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    # ---- extract transform ----

    transform = {}

    if "move" in args and args["move"][1][1]:
        translation = args["move"][0]
        translation[2] = translation[2].split('-')[-1]
        transform["move"] = translation

    if "rotation" in args and args["rotation"][1][1]:
        rotation = args["rotation"][0]
        rotation[2] = rotation[2].split('-')[-1]
        transform["rotation"] = rotation

    if "scal" in args and args["scal"][1][1]:
        scal = args["scal"][0]
        scal[2] = scal[2].split('-')[-1]
        transform["scal"] = scal

    entry = {
        "transform": transform
    }

    # ---- extract selected vector classes ----
    sel_drawings = args.get("sel_drawings")
    if sel_drawings and sel_drawings[1]:
        for item in sel_drawings[0]:
            mapped_targets = item["data_name"]

            content = (
                f"{mapped_targets} mapped"
                if mapped_targets
                else "vectors mapped"
            )

            clip = args.get("clip")

            if clip[1]:
                pos = clip[0].split('-')[-1]
                content = content + f" in clip {pos}"
                entry.update({"clip": pos})

            entry.update({"content": content,
                          "vector": item if mapped_targets else None})

            page_map[page].append(copy.deepcopy(entry))

def handle_delete_indiscriminate(op, page_map):
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]
    clip = args["clip"][0]

    page_map[page].append({
        "content": f"deleted all drawings in clip {clip.split('-')[-1]}",
        "clip": clip.split('-')[-1]
    })

def handle_repair_vectors(op, page_map):
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    sel_drawings = args.get("sel_drawings", (None, False))[0]

    entry = {}

    if sel_drawings:
        repaired_classes = sorted(
            {item.get("data_name", "drawings") for item in sel_drawings}
        )
        content_desc = f"repaired {', '.join(repaired_classes)}"
    else:
        content_desc = "repaired drawings indiscriminately"

    clip = args.get("clip")

    if clip[1]:
        pos = clip[0].split('-')[-1]
        content_desc = content_desc + f" in clip {pos}"
        entry.update({"clip": pos})

    entry.update({
        "content": content_desc,
    })

    page_map[page].append(entry)

def handle_table_manipulator(op, page_map):
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]
    tool_calls = op.get("tool_callings", [])

    # ---- classify operation type ----
    tool_names = {tc["tool_name"] for tc in tool_calls}

    has_structural_edit = bool(
        {"empty_table", "modify_table", "cut_table"} & tool_names
    )

    is_refresh = False
    data_arg = args.get("data")

    data_value = None
    if data_arg and data_arg[1]:
        data_value = data_arg[0]
        if (
                isinstance(data_value, list)
                and len(data_value) == 1
                and isinstance(data_value[0], list)
                and data_value[0]
                and isinstance(data_value[0][0], dict)
                and data_value[0][0].get("data_name") == "table_data"
        ):
            is_refresh = True



    if has_structural_edit:
        content_desc = "table revised"
    elif is_refresh:
        content_desc = "table refreshed"
    else:
        content_desc = "table added"

    fmt = {}
    for k in ("font", "font_size", "border_width", "align", "arrange"):
        if k in args and args[k][1]:
            fmt[k] = args[k][0]

    clip = args.get("clip")
    entry = {
        "data": data_value
    }

    # ---- detailed revise summary ----
    if content_desc == "table revised":
        operations = []

        for tc in tool_calls:
            args_dict = extract_tool_arguments(tc)

            if tc["tool_name"] == "empty_table":
                operations.append({
                    "type": "clear",
                    "start_cell": args_dict.get("start_cell"),
                    "end_cell": args_dict.get("end_cell"),
                })

            elif tc["tool_name"] == "modify_table":
                operations.append({
                    "type": "replace",
                    "start_cell": args_dict.get("start_cell"),
                    "end_cell": args_dict.get("end_cell"),
                    "rep_data": args_dict.get("rep_data"),
                })

            elif tc["tool_name"] == "cut_table":
                operations.append({
                    "type": "delete",
                    "delrow": args_dict.get("delrow"),
                    "delcolumn": args_dict.get("delcolumn"),
                })

        if operations:
            entry["operations"] = operations

    if clip[1]:
        pos = clip[0].split('-')[-1]
        if content_desc == "table revised":
            content_desc = content_desc + f" in clip {pos}" + f" extracted from {args['doc'][0]}, page {args['page'][0]}, clip {args['clip'][0]}"
        else:
            content_desc = content_desc + f" in clip {pos}"
        entry.update({"clip": pos})

    entry.update({"content": content_desc})

    if fmt:
        entry.update({"format": fmt})

    if page_map[page]:
        page_map[page][0] = entry
    else:
        page_map[page].append(entry)

def handle_text_manipulator(op, page_map):
    """
    Handle add_text / text insertion operations.
    """
    if not op.get("save"):
        return

    args = dict(op["arguments_value"])
    page = args["page"][0]

    # ---- detect refresh vs add ----
    tool_calls = op.get("tool_callings", [])

    for call in reversed(range(0, len(tool_calls))):
        if tool_calls[call]["tool_name"] != "add_text":
            tool_calls.pop(call)
        else:
            break


    tool_names = [tc["tool_name"] for tc in tool_calls]

    has_revise = any(
        name in ("delete_text", "replace_text")
        for name in tool_names
    )


    has_refresh = any(
        name in ("get_ver_text", "get_hor_text")
        for name in tool_names
    )



    if has_refresh or has_revise:
        text = args.get("text")[0]
        # rotate = args.get("rotate")
        # direction = "vertical" if rotate[0] == 90 else "horizontal"

    if has_revise:
        content_label = f"{text if text != 'Unknown' else 'Unknown text'} revised"
    elif has_refresh:
        content_label = f"{text if text != 'Unknown' else 'Unknown text'} refreshed"
    else:
        content_label = f"new text added '{args['text'][0]}'"

    clip = args.get("clip")

    entry = {}
    entry = {
        "data": args.get("text")[0]
    }

    if clip[1]:
        pos = clip[0].split('-')[-1]
        content_label = content_label + f" in clip {pos}"
        entry.update({"clip": pos})

    entry.update({"content": content_label})

    # ---- detailed revise summary ----
    if "revised" in content_label:
        operations = []

        for tc in tool_calls:
            args_dict = extract_tool_arguments(tc)

            if tc["tool_name"] == "delete_text":
                operations.append({
                    "type": "delete",
                    "deltex": args_dict.get("deltex"),
                })

            elif tc["tool_name"] == "replace_text":
                operations.append({
                    "type": "replace",
                    "retext": args_dict.get("retext"),
                    "totext": args_dict.get("totext"),
                })

        if operations:
            entry["operations"] = operations

    fmt = {}
    for k in ("font", "fontsize", "textcolor", "fill", "rotate", "align"):
        if k in args and args[k][1]:
            fmt[k] = args[k][0]

    if fmt:
        entry["format"] = fmt
    if page_map[page]:
        page_map[page][0] = entry
    else:
        page_map[page].append(entry)

OPERATION_HANDLERS = {
    "instantiate_drawing_manipulator": handle_drawing_manipulator,
    "instantiate_table_manipulator": handle_table_manipulator,
    "instantiate_text_manipulator": handle_text_manipulator,
    "instantiate_drawer": handle_delete_selected_vectors,
    "instantiate_cleaner": handle_delete_indiscriminate,
    "instantiate_repairer": handle_repair_vectors,
    "instantiate_projector": handle_projector,
    "instantiate_draw_projector": handle_draw_projector,

}

def extract_page_contents_with_registry(chain):
    page_map = defaultdict(list)

    for phase in ("change_maker", "post_change_maker"):

        if phase not in chain:
            return page_map

        for op in chain[phase]:


            if not op.get("save"):
                continue

            operation = op.get("operation")
            handler = OPERATION_HANDLERS.get(operation)

            if handler:
                handler(op,page_map)

    return page_map


def operation_chain_to_file_dict(operation_chain):
    file_dicts = []

    for chain in operation_chain:
        # determine final filename
        orignal_file_name = chain['filepath'][0]
        final_name = get_final_filename(chain)
        if not final_name:
            continue

        pages_content = extract_page_contents_with_registry(chain)

        pages = []
        for page_num, contents in pages_content.items():
            pages.append({
                "page_num": page_num,
                "contents": contents
            })

        file_dicts.append({
            "filename": orignal_file_name + ',' + final_name,
            "page": pages
        })

    return file_dicts


def extract_record_descriptions(operation_chain):
    records = []
    for chain in operation_chain:
        filepath = chain.get("filepath", ["missing"])[0]
        for recorder in chain.get("recorder", []):
            arguments = extract_tool_arguments(recorder)
            records.append({
                "filename": filepath,
                "page": arguments.get("page"),
                "clip": (
                    arguments.get("clip").split("-")[-1]
                    if isinstance(arguments.get("clip"), str)
                    else arguments.get("clip")
                ),
                "action": arguments.get("action"),
                "complete": arguments.get("complete"),
            })
    return records


def modification_description_from_chain(operation_chain):
    chain_copy = copy.deepcopy(operation_chain)
    return {
        "files": operation_chain_to_file_dict(chain_copy),
        "records": extract_record_descriptions(chain_copy),
    }


def _canonicalize(value):
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(canonical_items, key=lambda item: repr(item))
    if isinstance(value, tuple):
        return _canonicalize(list(value))
    return value


def modification_descriptions_match(predicted_chain, reference_chain):
    try:
        predicted_description = modification_description_from_chain(predicted_chain)
        reference_description = modification_description_from_chain(reference_chain)
    except Exception:
        return False
    return _canonicalize(predicted_description) == _canonicalize(reference_description)

def get_or_create_page(file_dict, page_num):
    for page in file_dict["page"]:
        if page["page_num"] == page_num:
            return page

    new_page = {"page_num": page_num, "contents": []}
    file_dict["page"].append(new_page)
    return new_page

def is_delete_entry(entry):
    """
    True if the entry represents a deletion.
    """
    # vector delete
    if entry.get("content", "").startswith("delete"):
        return True

    if entry.get("content", "").endswith("deleted"):
        return True

    #table revise with delete ops only
    if "table revised" in entry.get("content", ""):
        ops = entry.get("operations", [])
        delete_or_not = False
        for op in ops:
            if op["type"] == "delete":
                if (not op.get("delcolumn", None)) and (not op.get("delrow", None)):
                    delete_or_not = True
        return delete_or_not

    # text revise with delete ops only
    if "text" in entry.get("content", "") and "revised" in entry.get("content", ""):
        ops = entry.get("operations", [])
        delete_or_not = False
        delete_idx = None
        for o, op in enumerate(ops):
            if op["type"] == "delete":
                if not op.get("deltex", None):
                    delete_or_not = True
                    delete_idx = o

        if delete_idx:
            for count in range(int(delete_idx)):
                entry["operations"].pop(count)
        return delete_or_not

    return False

def apply_table_operations(old_data, operations):
    """
    Apply structural table edits to previous table data.
    old_data: 2D list
    operations: list of operation dicts
    """
    if not old_data:
        return old_data

    table = copy.deepcopy(old_data)

    for op in operations:
        if op["type"] == "clear":
            # empty cell range
            start = op.get("start_cell")
            end = op.get("end_cell")
            if start and end:
                for r in range(start[0], end[0] + 1):
                    for c in range(start[1], end[1] + 1):
                        table[r][c] = ""

        elif op["type"] == "replace":
            start = op.get("start_cell")
            end = op.get("end_cell")
            rep = op.get("rep_data")
            if start and end and rep:
                idx = 0
                for r in range(start[0], end[0] + 1):
                    for c in range(start[1], end[1] + 1):
                        table[r][c] = rep[idx]
                        idx += 1

        elif op["type"] == "delete":
            delrow = op.get("delrow")
            delcolumn = op.get("delcolumn")

            if delrow:
                for r in sorted(delrow, reverse=True):
                    if r < len(table):
                        table.pop(r)

            if delcolumn:
                for r in range(len(table)):
                    for c in sorted(delcolumn, reverse=True):
                        if c < len(table[r]):
                            table[r].pop(c)

    return table

def find_entry_by_clip(contents, clip, vector=None):
    """
    Return (index, entry) of the first entry whose clip matches.
    If not found, return (-1, None).
    """
    i = 0
    while i < len(contents):
        if contents[i].get("clip") == clip:
            if vector:
                if "vector" in list(contents[i].keys()):
                    if contents[i].get("vector") == vector:
                        return i, contents[i]
            else:
                return i, contents[i]
        i += 1
    return -1, None

def merge_format(old_fmt, new_fmt):
    if not old_fmt and not new_fmt:
        return None
    if not old_fmt:
        return dict(new_fmt)
    if not new_fmt:
        return dict(old_fmt)

    merged = dict(old_fmt)
    for k, v in new_fmt.items():
        if v is not None:
            merged[k] = v
    return merged

def merge_transform(old_t, new_t):
    if not old_t:
        return new_t
    if not new_t:
        return old_t

    merged = dict(old_t)
    for k, v in new_t.items():
        merged[k] = v  # latest wins (can later upgrade to matrix compose)
    return merged

def merge_operations(old_ops, new_ops):
    old_list = old_ops if isinstance(old_ops, list) else []
    new_list = new_ops if isinstance(new_ops, list) else []
    if not old_list and not new_list:
        return None
    return old_list + new_list

def merge_entry_into_page(old_filename, contents, new_entry):
    clip = new_entry.get("clip")
    vector = new_entry.get("vector", None)
    if clip is None:
        # no clip => cannot merge by clip identity; append as-is
        contents.append(new_entry)
        return

    new_is_delete = is_delete_entry(new_entry)
    idx, old_entry = find_entry_by_clip(contents, clip, vector)
    if old_entry:
        if new_entry.get("content") and old_entry.get("content"):
            extract_patttern = re.compile(f'extracted from (.*), page (\d*), clip .*-(\d*)')
            old_extracted = extract_patttern.search(old_entry.get("content"))
            new_extracted = extract_patttern.search(new_entry.get("content"))
            if old_extracted and new_extracted:
                if new_extracted.group(1) == old_filename and new_extracted.group(2) == old_extracted.group(2) and new_extracted.group(3) == old_extracted.group(3):
                    new_entry["content"] = old_entry["content"]
                else:
                    old_entry["operations"] = []
            elif new_extracted:
                if new_extracted.group(1) == old_filename and new_extracted.group(3) == clip:
                    new_entry["data"] = old_entry["data"]
                else:
                    old_entry["operations"] = []
            else:
                old_entry["operations"] = []

    if new_is_delete:
        # Delete semantics:
        # if existing entry at same clip is non-delete, remove it.
        if idx != -1 and not is_delete_entry(old_entry):
            contents.pop(idx)
            idx = -1
            old_entry = None
        # If there is already a delete entry at same clip, merge format
        elif idx != -1 and old_entry is not None:
            # merged_ops = merge_operations(old_entry.get("operations"), new_entry.get("operations"))
            # if merged_ops is not None:
            #     old_entry["operations"] = merged_ops

            merged_fmt = merge_format(old_entry.get("format"), new_entry.get("format"))
            if merged_fmt is not None:
                old_entry["format"] = merged_fmt

            # content label: keep old unless you want latest wording
            old_entry["content"] = new_entry.get("content", old_entry.get("content"))
        else:
            contents.append(new_entry)
        return

    # Non-delete accumulation:
    # if same clip exists => MERGE, else append
    if idx == -1:
        contents.append(new_entry)
        return

    if "transform" in new_entry:
        old_entry["transform"] = merge_transform(
            old_entry.get("transform"),
            new_entry.get("transform")
        )

    # ----- TABLE SPECIAL LOGIC -----
    if "table" in new_entry.get("content", ""):

        old_data = old_entry.get("data")
        new_data = new_entry.get("data")

        # If new table fully replaces
        if new_data:
            old_entry["data"] = copy.deepcopy(new_data)

        # If revise operations exist → apply to previous table
        # if new_entry.get("operations"):
        #     # updated_table = apply_table_operations(
        #     #     old_entry.get("data"),
        #     #     new_entry.get("operations")
        #     # )
        #     old_entry["operations"].extend(new_entry.get("operations"))

    # Merge operations at the end
    merged_ops = merge_operations(old_entry.get("operations"), new_entry.get("operations"))
    if merged_ops is not None:
        old_entry["operations"] = merged_ops

    # Merge format (new overrides old)
    merged_fmt = merge_format(old_entry.get("format"), new_entry.get("format"))
    if merged_fmt is not None:
        old_entry["format"] = merged_fmt

    # Update content label if the new one is "more specific" (optional, but useful)
    # Simple rule: always take the latest label
    if new_entry.get("content") is not None:
        old_entry["content"] = new_entry["content"]

    # Carry over any other fields you may have added (optional)
    # Example: keep latest "details" if present
    if "details" in new_entry:
        old_entry["details"] = new_entry["details"]

def merge_file_dict(existing_file, new_file):
    """
    Update existing_file in-place using new_file.
    """
    for new_page in new_file["page"]:
        page_num = new_page["page_num"]
        target_page = get_or_create_page(existing_file, page_num)

        for new_entry in new_page["contents"]:
            merge_entry_into_page(existing_file['filename'], target_page["contents"], new_entry)

            # clip = new_entry.get("clip")
            # delete_flag = is_delete_entry(new_entry)
            #
            # if delete_flag:
            #     # remove any non-deletion content at same clip
            #     target_page["contents"] = [
            #         e for e in target_page["contents"]
            #         if e.get("clip") != clip or is_delete_entry(e)
            #     ]
            # else:
            #     # accumulate
            #     target_page["contents"].append(new_entry)

def apply_operation_chains(
    file_dicts,
    operation_chains,
    chain_to_file_dict_func
):
    """
    file_dicts: List of existing file dictionaries
    operation_chains: List of new operation chains
    chain_to_file_dict_func: your phase-1 converter
    """
    file_index = {
        f["filename"]: f
        for f in file_dicts
    }
    files = list(file_index.keys())
    file_list = [f.split(',')[1] for f in file_index]
    for chain in operation_chains:
        new_file = chain_to_file_dict_func([chain])
        filenames = [x["filename"] for x in new_file]
        for j in range(len(filenames)):
            filename = filenames[j].split(',')

            if filename[0] in file_list:
                index = file_list.index(filename[0])
                merge_file_dict(file_index[files[index]], new_file[j])
            else:
                file_dicts.extend(new_file)
                file_index[filenames[j]] = new_file

    return file_dicts


def flatten_file_dict(file_dict):
    """
    Convert file_dict to {(page, clip): entry}
    """
    mapping = {}
    for page in file_dict["page"]:
        page_num = page["page_num"]
        for entry in page["contents"]:
            mapping[(page_num, entry["clip"])] = entry
    return mapping

def operation_f1(pred_ops, gt_ops):
    pred_types = [op["type"] for op in pred_ops]
    gt_types = [op["type"] for op in gt_ops]

    tp = sum(1 for t in pred_types if t in gt_types)
    precision = tp / len(pred_types) if pred_types else 0
    recall = tp / len(gt_types) if gt_types else 0

    if precision + recall == 0:
        return 0
    return 2 * precision * recall / (precision + recall)

def argument_score(pred_ops, gt_ops):
    score = 0
    count = 0

    for gt_op in gt_ops:
        for pred_op in pred_ops:
            if pred_op["type"] == gt_op["type"]:
                fields = set(gt_op.keys()) - {"type"}
                if not fields:
                    score += 1
                else:
                    match = 0
                    for f in fields:
                        if pred_op.get(f) == gt_op.get(f):
                            match += 1
                    score += match / len(fields)
                count += 1
                break

    return score / count if count else 0

def format_score(pred_fmt, gt_fmt):
    if not gt_fmt:
        return 1.0

    correct = 0
    for k, v in gt_fmt.items():
        if pred_fmt and pred_fmt.get(k) == v:
            correct += 1

    return correct / len(gt_fmt)

def evaluate_file(pred_file, gt_file,
                  alpha=0.3, beta=0.5, gamma=0.2):

    pred_map = flatten_file_dict(pred_file)
    gt_map = flatten_file_dict(gt_file)

    matched_clips = 0
    op_scores = []
    fmt_scores = []

    for key, gt_entry in gt_map.items():
        if key in pred_map:
            matched_clips += 1
            pred_entry = pred_map[key]

            # operations
            pred_ops = pred_entry.get("operations", [])
            gt_ops = gt_entry.get("operations", [])
            type_f1 = operation_f1(pred_ops, gt_ops)
            arg_score = argument_score(pred_ops, gt_ops)
            op_scores.append(0.5 * type_f1 + 0.5 * arg_score)

            # format
            fmt_scores.append(
                format_score(
                    pred_entry.get("format", {}),
                    gt_entry.get("format", {})
                )
            )

    clip_score = matched_clips / len(gt_map) if gt_map else 0
    operation_score = sum(op_scores) / len(op_scores) if op_scores else 0
    format_score_avg = sum(fmt_scores) / len(fmt_scores) if fmt_scores else 0

    final_score = (
        alpha * clip_score +
        beta * operation_score +
        gamma * format_score_avg
    )

    return {
        "clip_score": clip_score,
        "operation_score": operation_score,
        "format_score": format_score_avg,
        "final_score": final_score
    }

WRITE_TOOL_NAMES = {
    "add_text", "add_table",
    "update_drawings", "delete_drawings", "clean_drawings",
    "project",
    "repair_drawings",
}

EXTRACT_TOOL_NAMES = {
    "exract_rect", "exract_anno",
    "select_mode1_drawings", "select_mode2_drawings",
    "select_mode1_lines", "select_mode2_lines",
    "select_mode1_rebars", "select_mode2_rebars",
    "select_mode1_columns", "select_mode2_columns",
}

def efficiency_from_operation_chains(operation_chains, k=20.0):
    tool_calls = 0
    write_calls = 0
    extract_calls = 0

    for chain in operation_chains:
        for stage_key in ("extractor", "table_extractor", "selector", "change_maker", "post_change_maker", "recorder"):
            for op in chain.get(stage_key, []):
                for tc in op.get("tool_callings", []):
                    tool_calls += 1
                    name = tc.get("tool_name")
                    if name in WRITE_TOOL_NAMES:
                        write_calls += 1
                    if name in EXTRACT_TOOL_NAMES:
                        extract_calls += 1

    cost = 1.0 * tool_calls + 2.0 * write_calls + 0.5 * extract_calls
    eff = 1.0 / (1.0 + cost / k)
    return {
        "tool_calls": tool_calls,
        "write_calls": write_calls,
        "extract_calls": extract_calls,
        "cost": cost,
        "efficiency": eff
    }

def combined_score(correctness_score, efficiency_score):
    return correctness_score * efficiency_score

def compute_turn_accuracies(pred_states, gt_states, evaluator):
    """
    pred_states[t], gt_states[t]
    evaluator: evaluate_file function
    """
    T = len(gt_states)
    acc = []

    for t in range(T):
        score_dict = evaluator(pred_states[t], gt_states[t])
        acc.append(score_dict["final_score"])

    return acc

def mean_accuracy(acc):
    return sum(acc) / len(acc) if acc else 0
