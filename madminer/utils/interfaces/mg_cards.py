import logging

from collections import OrderedDict
from typing import Dict

from madminer.models import AnalysisParameter
from madminer.models import Benchmark
from madminer.models import Systematic
from madminer.models import SystematicScale
from madminer.models import SystematicType


logger = logging.getLogger(__name__)


def export_param_card(
    benchmark: Benchmark,
    parameters: Dict[str, AnalysisParameter],
    param_card_template_file: str,
    mg_process_directory: str,
    param_card_filename: str = None,
):
    # Open parameter card template
    with open(param_card_template_file) as file:
        param_card = file.read()
    lines = param_card.splitlines()

    # Replace parameter values
    for param_name, param_value in benchmark.values.items():
        param_lha_block = parameters[param_name].lha_block
        param_lha_id = parameters[param_name].lha_id
        param_transform = parameters[param_name].transform

        # Transform parameters if needed
        if param_transform is not None:
            variables = {"theta": param_value}
            param_value = eval(param_transform, variables)

        param_value = float(param_value)

        # Find entry
        current_block = None
        changed_line = False
        for i, line in enumerate(lines):

            # Remove comment
            try:
                line = line.split("#")[0]
            except:
                pass

            elements = line.split()

            # See if block begin
            if len(elements) == 2 and elements[0].lower() == "block":
                current_block = elements[1].lower()

            elif len(elements) == 2 and param_lha_block.lower() == current_block:
                try:
                    lha_id = int(elements[0])
                except ValueError:
                    continue

                if lha_id == param_lha_id:
                    lines[i] = f"    {param_lha_id}    {param_value}    # MadMiner"
                    changed_line = True
                    break

            elif len(elements) == 3 and elements[0].lower() == param_lha_block.lower():
                try:
                    lha_id = int(elements[1])
                except ValueError:
                    continue

                current_block = None
                if lha_id == param_lha_id:
                    lines[i] = f"{param_lha_block}    {param_lha_id}    {param_value}    # MadMiner"
                    changed_line = True
                    break

        if not changed_line:
            raise ValueError(f"Could not find LHA ID {param_lha_id} in param_card template!")

        param_card = "\n".join(lines)

    # Output filename
    if param_card_filename is None:
        param_card_filename = f"{mg_process_directory}/Cards/param_card.dat"

    # Save param_card.dat
    with open(param_card_filename, "w") as file:
        file.write(param_card)


def export_reweight_card(
    sample_benchmark: Benchmark,
    benchmarks: Dict[str, Benchmark],
    parameters: Dict[str, AnalysisParameter],
    mg_process_directory: str,
    reweight_card_filename: str = None,
):
    # Global setup
    lines = [
        "# Reweight card generated by MadMiner",
        "",
        "# Global setup",
        "change output default",
        "change helicity False",
    ]

    for benchmark_name, benchmark in benchmarks.items():
        if benchmark_name == sample_benchmark:
            continue

        lines.append("")
        lines.append("# MadMiner benchmark " + benchmark_name)
        lines.append("launch --rwgt_name=" + benchmark_name)

        for param_name, param_value in benchmark.values.items():
            param_lha_block = parameters[param_name].lha_block
            param_lha_id = parameters[param_name].lha_id
            param_transform = parameters[param_name].transform

            # Transform parameters if needed
            if param_transform is not None:
                variables = {"theta": param_value}
                param_value = eval(param_transform, variables)

            lines.append(f"  set {param_lha_block} {param_lha_id} {param_value}")

        lines.append("")

    reweight_card = "\n".join(lines)

    # Output filename
    if reweight_card_filename is None:
        reweight_card_filename = f"{mg_process_directory}/Cards/reweight_card.dat"

    # Save param_card.dat
    with open(reweight_card_filename, "w") as file:
        file.write(reweight_card)


def export_run_card(
    template_filename: str,
    run_card_filename: str,
    systematics: Dict[str, Systematic] = None,
    order: str = "LO",
):
    # Open parameter card template
    with open(template_filename) as file:
        run_card_template = file.read()

    run_card_lines = run_card_template.split("\n")

    # Do we actually have to run MadGraph's systematics feature?
    run_systematics = False
    for syst in systematics.values():
        if syst.type in {SystematicType.PDF, SystematicType.SCALE}:
            run_systematics = True
            break

    # Lines to be removed
    entries_to_comment_out = [
        "use_syst",
        "systematics_program",
        "systematics_argument",
        "systematics_arguments",
        "sys_scalefact",
        "sys_alpsfact",
        "sys_matchscale",
        "sys_pdf",
    ]

    # Changes to be made
    settings = OrderedDict()
    settings["use_syst"] = "False"
    if run_systematics:
        settings["use_syst"] = "True"
        settings["systematics_program"] = "systematics"
        settings["systematics_arguments"] = create_systematics_arguments(systematics)

    # Remove old entries
    for i, line in enumerate(run_card_lines):
        line_content = line
        # Remove comments
        try:
            line_content = line_content.split("#")[0]
        except:
            pass
        try:
            line_content = line_content.split("!")[0]
        except:
            pass

        # Split at last equal sign
        elements = line_content.split("=")
        if len(elements) < 2:
            continue
        line_key = elements[-1].strip()

        if line_key in entries_to_comment_out:
            run_card_lines[i] = f"# {line} # Commented out by MadMiner"
            continue

    # Add new entries - systematics
    if order == "LO":
        run_card_lines.append("")
        run_card_lines.append("#*********************************************************************")
        run_card_lines.append("# MadMiner systematics setup                                         *")
        run_card_lines.append("#*********************************************************************")
        for key, value in settings.items():
            run_card_lines.append(f"{value} = {key}")
        run_card_lines.append("")

    # Write new run card
    new_run_card = "\n".join(run_card_lines)
    with open(run_card_filename, "w") as file:
        file.write(new_run_card)


def create_systematics_arguments(systematics: Dict[str, Systematic]):
    """ Put together systematics_arguments string for MadGraph run card """

    if systematics is None:
        return ""

    systematics_arguments = []

    mur_done = False
    muf_done = False
    pdf_done = False

    for systematic in systematics.values():

        if systematic.type == SystematicType.SCALE and systematic.scale == SystematicScale.MU:
            if mur_done or muf_done:
                raise ValueError("Multiple nuisance parameter for scale variation!")
            systematics_arguments.append(f"'--mur={systematic.value}'")
            systematics_arguments.append(f"'--muf={systematic.value}'")
            systematics_arguments.append(f"'--together=mur,muf'")
            systematics_arguments.append(f"'--dyn=-1'")
            mur_done = True
            muf_done = True

        elif systematic.type == SystematicType.SCALE and systematic.scale == SystematicScale.MUR:
            if mur_done:
                raise ValueError("Multiple nuisance parameter for mur variation!")
            systematics_arguments.append(f"'--mur={systematic.value}'")
            systematics_arguments.append(f"'--dyn=-1'")
            mur_done = True

        elif systematic.type == SystematicType.SCALE and systematic.scale == SystematicScale.MUF:
            if muf_done:
                raise ValueError("Multiple nuisance parameter for muf variation!")
            systematics_arguments.append(f"'--muf={systematic.value}'")
            systematics_arguments.append(f"'--dyn=-1'")
            muf_done = True

        elif systematic.type == SystematicType.PDF:
            if pdf_done:
                raise ValueError("Multiple nuisance parameter for PDF variation!")
            systematics_arguments.append(f"'--pdf={systematic.value}'")
            pdf_done = True

    if len(systematics_arguments) > 0:
        return f"[{', '.join(systematics_arguments)}]"

    return ""
