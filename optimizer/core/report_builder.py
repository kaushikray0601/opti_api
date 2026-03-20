from collections import defaultdict


def build_schedule_output(
    cable_rows,
    drum_rows,
    drum_data,
    drum_schedule,
    revision_number,
):
    json_output = []

    for scheduled_type in drum_schedule:
        for scheduled_drum in scheduled_type:
            drum_index = int(scheduled_drum[0])
            drum_tag = drum_rows[drum_index, 0]
            cable_spec = drum_rows[drum_index, 1]
            drum_length = int(drum_data[drum_index, 2])
            drum_leftover = int(scheduled_drum[1][0])

            allotted_cables = scheduled_drum[1][1]
            cable_input_seq = []
            cable_tags = []
            cable_lengths = []
            wbs_values = []
            pull_card_numbers = []

            for cable_index in allotted_cables:
                cable_index = int(cable_index)
                cable_input_seq.append(cable_index)
                cable_tags.append(cable_rows[cable_index, 0])
                cable_lengths.append(int(cable_rows[cable_index, 1]))
                wbs_values.append(cable_rows[cable_index, 3])
                pull_card_numbers.append("PC_" + cable_rows[cable_index, 0])

            json_output.append(
                [
                    [cable_spec, drum_index, drum_tag, drum_length, drum_leftover],
                    cable_input_seq,
                    cable_tags,
                    cable_lengths,
                    wbs_values,
                    pull_card_numbers,
                    revision_number,
                ]
            )

    return json_output


def build_report(cable_rows, drum_rows, json_output):
    cable_records = _build_cable_records(cable_rows)
    drum_records = _build_drum_records(drum_rows)

    unique_cable_types = list(dict.fromkeys(record[3] for record in cable_records))
    unique_drum_types = list(dict.fromkeys(record[2] for record in drum_records))
    unique_wbs = list(dict.fromkeys(record[4] for record in cable_records))

    cable_length = sum(record[2] for record in cable_records)
    drum_length = sum(record[3] for record in drum_records)

    allocated_drum_rows = [entry[0] for entry in json_output]
    allocated_cable_groups = [entry[1] for entry in json_output]

    allocation_by_cable_index = {}
    allocated_cable_count = 0
    allocated_cable_length = 0
    allocated_drum_indices = []
    allotted_dr_list = []
    allotted_dr_summary_totals = defaultdict(lambda: [0, 0])
    partial_spare_drum_count = 0
    partial_spare_drum_length = 0

    for drum_row, cable_indexes in zip(allocated_drum_rows, allocated_cable_groups):
        cable_spec = drum_row[0]
        drum_index = int(drum_row[1])
        drum_tag = drum_row[2]
        current_drum_length = int(drum_row[3])
        current_drum_leftover = int(drum_row[4])

        allotted_dr_list.append(
            [cable_spec, drum_index, drum_tag, current_drum_length, current_drum_leftover]
        )
        allocated_drum_indices.append(drum_index)

        summary_row = allotted_dr_summary_totals[cable_spec]
        summary_row[0] += current_drum_length
        summary_row[1] += current_drum_leftover

        if current_drum_leftover > 0:
            partial_spare_drum_count += 1
            partial_spare_drum_length += current_drum_leftover

        for cable_index in cable_indexes:
            cable_index = int(cable_index)
            allocation_by_cable_index[cable_index] = (drum_tag, drum_index)
            allocated_cable_count += 1
            allocated_cable_length += cable_records[cable_index][2]

    allotted_drum_index_set = set(allocated_drum_indices)
    allot_cab_summary_totals = defaultdict(int)
    unallot_cab_summary_totals = defaultdict(int)
    allot_cab_list = []
    unallot_cab_list = []

    for cable_record in cable_records:
        cable_index = cable_record[0]
        cable_length_value = cable_record[2]
        cable_type = cable_record[3]
        wbs_value = cable_record[4]

        if cable_index in allocation_by_cable_index:
            drum_tag, drum_index = allocation_by_cable_index[cable_index]
            allot_cab_summary_totals[cable_type] += cable_length_value
            allot_cab_list.append(cable_record + [drum_tag, drum_index])
        else:
            unallot_cab_summary_totals[(wbs_value, cable_type)] += cable_length_value
            unallot_cab_list.append(cable_record.copy())

    unallot_dr_list = []
    unallot_dr_summary_totals = defaultdict(int)
    for drum_record in drum_records:
        drum_index = drum_record[0]
        drum_type = drum_record[2]
        drum_length_value = drum_record[3]
        if drum_index not in allotted_drum_index_set:
            unallot_dr_list.append(drum_record.copy())
            unallot_dr_summary_totals[drum_type] += drum_length_value

    ds_stat = {
        "no_of_cables": len(cable_records),
        "cable_length": int(cable_length),
        "no_of_type_of_cables": len(unique_cable_types),
        "no_of_WBS": len(unique_wbs),
        "no_of_drums": len(drum_records),
        "drum_length": int(drum_length),
        "no_of_type_of_drums": len(unique_drum_types),
        "no_of_unAllotted_cables": len(unallot_cab_list),
        "unAllotted_cables_length": int(sum(record[2] for record in unallot_cab_list)),
        "cabType_with_NO_drum": len(set(unique_cable_types) - set(unique_drum_types)),
        "no_of_allotted_cables": int(allocated_cable_count),
        "allotted_cable_length": int(allocated_cable_length),
        "no_of_drums_used": len(allotted_dr_list),
        "no_of_full_spare_drums": len(unallot_dr_list),
        "full_spare_drum_length": int(sum(record[3] for record in unallot_dr_list)),
        "no_of_partial_spare_drums": int(partial_spare_drum_count),
        "partial_spare_drum_length": int(partial_spare_drum_length),
        "no_of_joints": 0,
        "wastage": 0,
        "wastage_indicator": 0,
    }

    return {
        "statistics": ds_stat,
        "unallot_cab_summary": _build_wbs_type_summary_rows(unallot_cab_summary_totals),
        "unallot_cab_list": unallot_cab_list,
        "allot_cab_summary": _build_type_summary_rows(allot_cab_summary_totals),
        "allot_cab_list": allot_cab_list,
        "unallt_dr_summary": _build_type_summary_rows(unallot_dr_summary_totals),
        "unallot_dr_list": unallot_dr_list,
        "allot_dr_summary": _build_drum_summary_rows(allotted_dr_summary_totals),
        "allot_dr_list": allotted_dr_list,
    }


def _build_cable_records(cable_rows):
    return [
        [
            index,
            row[0],
            int(row[1]),
            row[2],
            row[3],
        ]
        for index, row in enumerate(cable_rows)
    ]


def _build_drum_records(drum_rows):
    return [
        [
            index,
            row[0],
            row[1],
            int(row[2]),
        ]
        for index, row in enumerate(drum_rows)
    ]


def _build_type_summary_rows(type_totals):
    summary_rows = []
    for row_index, cable_type in enumerate(sorted(type_totals)):
        summary_rows.append([row_index, cable_type, int(type_totals[cable_type])])
    return summary_rows


def _build_wbs_type_summary_rows(type_totals):
    summary_rows = []
    for row_index, (wbs_value, cable_type) in enumerate(sorted(type_totals)):
        summary_rows.append([row_index, wbs_value, cable_type, int(type_totals[(wbs_value, cable_type)])])
    return summary_rows


def _build_drum_summary_rows(type_totals):
    summary_rows = []
    for row_index, cable_type in enumerate(sorted(type_totals)):
        total_length, total_leftover = type_totals[cable_type]
        summary_rows.append([row_index, cable_type, int(total_length), int(total_leftover)])
    return summary_rows
