from typing import Sequence


def create_dp_table(target, cab_index, cab_len, cable_type=None):
    target = int(target)
    normalized_lengths = [int(length) for length in cab_len]
    search_table = [0 for _ in range(max(target, 0) + 1)]

    if target <= 0 or not normalized_lengths:
        return search_table, []

    aux_table = []
    first_length = normalized_lengths[0]
    if first_length <= target:
        search_table[first_length] = 1
        aux_table.append(first_length)

    for i in range(1, len(normalized_lengths)):
        current_length = normalized_lengths[i]
        if current_length > target:
            continue

        if search_table[current_length] == 0:
            search_table[current_length] = i + 1

        aux_table.sort()
        aux_pointer = len(aux_table)
        for j in range(aux_pointer):
            tmp_len = aux_table[j] + current_length
            if tmp_len < target:
                if search_table[tmp_len] == 0:
                    search_table[tmp_len] = i + 1
                    aux_table.append(tmp_len)
            elif tmp_len == target:
                search_table[tmp_len] = i + 1
                return search_table, aux_table
            else:
                break

        aux_table.append(current_length)

    return search_table, aux_table


def modified_search_algo(target, cab_index, cab_len, cable_type=None):
    target = int(target)
    if target <= 0 or len(cab_len) == 0:
        return [max(target, 0), []]

    normalized_lengths = [int(length) for length in cab_len]
    search_table, _ = create_dp_table(target, cab_index, normalized_lengths, cable_type)

    wastage = 0
    new_target = target

    while new_target > 0 and search_table[new_target] == 0:
        wastage += 1
        new_target = target - wastage

    result = []
    while new_target > 0:
        item_index = search_table[new_target] - 1
        result.append(cab_index[item_index])
        new_target = new_target - normalized_lengths[item_index]

    return [wastage, result]


def fill_drums_sequentially(
    filt_drum_index: Sequence,
    filt_drum_len: Sequence,
    cab_index: Sequence,
    cab_len: Sequence,
    cable_type=None,
):
    drum_schedule = []
    remaining_cable_index = list(cab_index)
    remaining_cable_len = [int(length) for length in cab_len]

    for drum_index, drum_length in zip(list(filt_drum_index), list(filt_drum_len)):
        if not remaining_cable_len:
            break

        allocation = modified_search_algo(
            int(drum_length),
            remaining_cable_index,
            remaining_cable_len,
            cable_type,
        )
        drum_schedule.append([drum_index, allocation])

        allocated_cables = set(allocation[1])
        if not allocated_cables:
            continue

        next_cable_index = []
        next_cable_len = []
        for current_index, current_length in zip(remaining_cable_index, remaining_cable_len):
            if current_index not in allocated_cables:
                next_cable_index.append(current_index)
                next_cable_len.append(current_length)

        remaining_cable_index = next_cable_index
        remaining_cable_len = next_cable_len

    return drum_schedule
