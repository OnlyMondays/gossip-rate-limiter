from typing import Dict

class GCounter:
    '''
    Grow-Only Counter CRDT (Conflic-free Replicated Data Type)

    General rules:
    - Each node only increments ITS OWN SLOT.
    - In order to merge two snapshots, take the max of each slot.
    - Sum all slots for the global count.
    '''

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.counts: Dict[str, int] = {node_id: 0}
    
    def increment(self) -> None:
        '''A node can only increment its own slot.'''
        self.counts[self.node_id] += 1

    def merge(self, incoming: Dict[str, int]) -> None:
        '''Merge a peer node's snapshot into ours; We take the max of each slot.'''
        for node_id, count in incoming.items():
            self.counts[node_id] = max(self.counts.get(node_id, 0), count)
    
    def total(self) -> int:
        '''Global request count -> sum all the slots accross the nodes'''
        return sum(self.counts.values())

    
    def snapshot(self) -> Dict[str, int]:
        '''Safe copy to send over the wire.'''
        return dict(self.counts)

    def reset(self) -> None:
        '''Called at the start of each new rate limit window.'''
        self.counts = {self.node_id: 0}