""" BUTTER PANEER BOT - FINAL SUBMISSION """

from collections import defaultdict, deque
import random  # Not used, still taken from simply.py sample submission
from typing import Optional, Tuple, Union, cast
from risk_helper.game import Game
from risk_shared.models.card_model import CardModel
from risk_shared.queries.query_attack import QueryAttack
from risk_shared.queries.query_claim_territory import QueryClaimTerritory
from risk_shared.queries.query_defend import QueryDefend
from risk_shared.queries.query_distribute_troops import QueryDistributeTroops
from risk_shared.queries.query_fortify import QueryFortify
from risk_shared.queries.query_place_initial_troop import QueryPlaceInitialTroop
from risk_shared.queries.query_redeem_cards import QueryRedeemCards
from risk_shared.queries.query_troops_after_attack import QueryTroopsAfterAttack
from risk_shared.queries.query_type import QueryType
from risk_shared.records.moves.move_attack import MoveAttack
from risk_shared.records.moves.move_attack_pass import MoveAttackPass
from risk_shared.records.moves.move_claim_territory import MoveClaimTerritory
from risk_shared.records.moves.move_defend import MoveDefend
from risk_shared.records.moves.move_distribute_troops import MoveDistributeTroops
from risk_shared.records.moves.move_fortify import MoveFortify
from risk_shared.records.moves.move_fortify_pass import MoveFortifyPass
from risk_shared.records.moves.move_place_initial_troop import MovePlaceInitialTroop
from risk_shared.records.moves.move_redeem_cards import MoveRedeemCards
from risk_shared.records.moves.move_troops_after_attack import MoveTroopsAfterAttack
from risk_shared.records.record_attack import RecordAttack
from risk_shared.records.types.move_type import MoveType
from typing import Set, Dict, Optional

####### GAME IMPORTS #######


# Bot State to Store Enemy Information --> DO NOT EDIT
class BotState():
    def __init__(self):
        self.enemy: Optional[int] = None

# Main Function Taken Directly From Scaffold --> DO NOT EDIT
def main():
    
    # Get the game object, which will connect you to the engine and
    # track the state of the game.
    game = Game()
    bot_state = BotState()
   
    # Respond to the engine's queries with your moves.
    while True:

        # Get the engine's query (this will block until you receive a query).
        query = game.get_next_query()

        # Based on the type of query, respond with the correct move.
        def choose_move(query: QueryType) -> MoveType:
            match query:
                case QueryClaimTerritory() as q:
                    return handle_claim_territory(game, bot_state, q)

                case QueryPlaceInitialTroop() as q:
                    return handle_place_initial_troop(game, bot_state, q)

                case QueryRedeemCards() as q:
                    return handle_redeem_cards(game, bot_state, q)

                case QueryDistributeTroops() as q:
                    return handle_distribute_troops(game, bot_state, q)

                case QueryAttack() as q:
                    return handle_attack(game, bot_state, q)

                case QueryTroopsAfterAttack() as q:
                    return handle_troops_after_attack(game, bot_state, q)

                case QueryDefend() as q:
                    return handle_defend(game, bot_state, q)

                case QueryFortify() as q:
                    return handle_fortify(game, bot_state, q)
        
        # Send the move to the engine.
        game.send_move(choose_move(query))
                
# Territory Selection Function --> For initial claiming stage
def handle_claim_territory(game: Game, bot_state: BotState, query: QueryClaimTerritory) -> MoveClaimTerritory:
    
    # Obtain set of unclaimed and owned territories at the beginning of turn
    unclaimed_territories = set(game.state.get_territories_owned_by(None))
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)

    # Try to form clusters of owned territories
    def count_adjacent_friendly(x: int) -> int:
        return len(set(my_territories) & set(game.state.map.get_adjacent_to(x)))
    
    # Territory Preferences and Initial Selection State
    na_territories_initial=[0,1,2,3,4,5,6,7,8]
    australian_territories=[38,39,40,41]
    selected_territory = -1

    # North America Selection and Clustering
    na_territories = sorted(na_territories_initial, key=lambda x: count_adjacent_friendly(x), reverse=True)
    i=0
    while i<len(na_territories):
        if(na_territories[i] in unclaimed_territories):
            selected_territory= na_territories[i]
            break
        i+=1

    # Australia Selection
    if selected_territory == -1:
        i=0
        while i<len(australian_territories):
            if(australian_territories[i] in unclaimed_territories):
                selected_territory = australian_territories[i]
                break
            i+=1

    # Clustering Of Owned Territories
    if selected_territory == -1:
        unclaimed_territories = game.state.get_territories_owned_by(None)
        my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
        adjacent_territories = game.state.get_all_adjacent_territories(my_territories)
        available = list(set(unclaimed_territories) & set(adjacent_territories))
        
        if len(available) != 0:

            # We will pick the one with the most connections to our territories
            def count_adjacent_friendly(x: int) -> int:
                return len(set(my_territories) & set(game.state.map.get_adjacent_to(x)))

            selected_territory = sorted(available, key=lambda x: count_adjacent_friendly(x), reverse=True)[0]
        
        # Otherwise pick a random territory
        else:
            selected_territory = sorted(unclaimed_territories, key=lambda x: len(game.state.map.get_adjacent_to(x)), reverse=True)[0]        

    return game.move_claim_territory(query, selected_territory)

# Initial Troop Placement Function --> For troop division at start of game
def handle_place_initial_troop(game: Game, bot_state: BotState, query: QueryPlaceInitialTroop) -> MovePlaceInitialTroop:
    
    # Place troops along the territories on our border
    border_territories = game.state.get_all_border_territories(
        game.state.get_territories_owned_by(game.state.me.player_id)
    )

    # Achieve somewhat equal distribution by placing troops on least occupied territory 
    border_territory_models = [game.state.territories[x] for x in border_territories]
    min_troops_territory = min(border_territory_models, key=lambda x: x.troops)

    return game.move_place_initial_troop(query, min_troops_territory.territory_id)

# Card Redemption Function --> For card-troop exchange upon risk card-set creation
def handle_redeem_cards(game: Game, bot_state: BotState, query: QueryRedeemCards) -> MoveRedeemCards:
    
    # We always have to redeem enough cards to reduce our card count below five.
    card_sets: list[Tuple[CardModel, CardModel, CardModel]] = []
    cards_remaining = game.state.me.cards.copy()

    while len(cards_remaining) >= 5:
        card_set = game.state.get_card_set(cards_remaining)
        # According to the pigeonhole principle, we should always be able to make a set
        # of cards if we have at least 5 cards.
        assert card_set != None
        card_sets.append(card_set)
        cards_remaining = [card for card in cards_remaining if card not in card_set]

    # Remember we can't redeem any more than the required number of card sets if 
    # we have just eliminated a player.
    if game.state.card_sets_redeemed > 0 and query.cause == "turn_started":
        card_set = game.state.get_card_set(cards_remaining)
        while card_set != None:
            card_sets.append(card_set)
            cards_remaining = [card for card in cards_remaining if card not in card_set]
            card_set = game.state.get_card_set(cards_remaining)

    return game.move_redeem_cards(query, [(x[0].card_id, x[1].card_id, x[2].card_id) for x in card_sets])

# Troop Distribution Function --> For troop division after card redemption
def handle_distribute_troops(game: Game, bot_state: BotState, query: QueryDistributeTroops) -> MoveDistributeTroops:
  
    distributions = defaultdict(lambda: 0)
    total_troops = game.state.me.troops_remaining

    # Distribute our matching territory bonus
    if len(game.state.me.must_place_territory_bonus) != 0:
        assert total_troops >= 2
        distributions[game.state.me.must_place_territory_bonus[0]] += 2
        total_troops -= 2

    # Send troops towards bordering territories
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    border_territories = game.state.get_all_border_territories(
        game.state.get_territories_owned_by(game.state.me.player_id)
    )
    border_territory_models = [game.state.territories[x] for x in border_territories]
    min_troops_territory = min(border_territory_models, key=lambda x: x.troops)
    
    distributions[min_troops_territory.territory_id] += total_troops
    return game.move_distribute_troops(query, distributions)

# Attack Function --> For attacking enemy territories
def handle_attack(game: Game, bot_state: BotState, query: QueryAttack) -> Union[MoveAttack, MoveAttackPass]:
    
    # Obtain owned and bordering territories
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    bordering_territories = game.state.get_all_adjacent_territories(my_territories)

    def attack_weakest(territories: list[int]) -> Optional[MoveAttack]:

        # We will attack the weakest territory from the list.
        territories = sorted(territories, key=lambda x: game.state.territories[x].troops)

        for candidate_target in territories:
            candidate_attackers = sorted(list(set(game.state.map.get_adjacent_to(candidate_target)) & set(my_territories)), key=lambda x: game.state.territories[x].troops, reverse=True)
            for candidate_attacker in candidate_attackers:
                if game.state.territories[candidate_attacker].troops > 1:
                    advantage=game.state.territories[candidate_attacker].troops - game.state.territories[candidate_target].troops
                    if advantage>=1:
                        return game.move_attack(query, candidate_attacker, candidate_target, min(3, game.state.territories[candidate_attacker].troops - 1))

    # Sort for attacking the weakest enemy territory from the strongest owned territory
    strongest_territories = sorted(my_territories, key=lambda x: game.state.territories[x].troops, reverse=True)
    for territory in strongest_territories:
        move = attack_weakest(list(set(game.state.map.get_adjacent_to(territory)) - set(my_territories)))
        if move != None:
            return move

    return game.move_attack_pass(query)

# Troop Movement Function --> For moving troops after successful attack
def handle_troops_after_attack(game: Game, bot_state: BotState, query: QueryTroopsAfterAttack) -> MoveTroopsAfterAttack:

    record_attack = cast(RecordAttack, game.state.recording[query.record_attack_id])
    move_attack = cast(MoveAttack, game.state.recording[record_attack.move_attack_id])
    attacking_territory = move_attack.attacking_territory
    defending_territory = move_attack.defending_territory
    troops = game.state.territories[attacking_territory].troops

    # Check if bordering territories of attacking territory are owned by us
    border_territories = game.state.get_all_border_territories([attacking_territory])

    # If no bordering territories, move all troops to the attacked territory
    if not border_territories:
        return game.move_troops_after_attack(query, troops - 1)
    
    # If bordering territories are owned by us, move half of troops to the attacked territory
    # Also move arbitrary number upon specified cases
    else:
        if defending_territory in border_territories:
            troops_deployed = (game.state.territories[attacking_territory].troops - 1)//2

        if troops > 20:
            troops_deployed = troops // 2 
        elif troops > 15:
            troops_deployed = troops - 5
        elif troops > 10:
            troops_deployed = troops - 4
        elif troops > 5:
            troops_deployed = troops - 3
        else:
            troops_deployed = troops - 1

        # Calculate Troops to Move According to Max Movable and Deployed Troops
        max_troops_to_move = game.state.territories[attacking_territory].troops - 1
        troops_to_move = min(troops_deployed, max_troops_to_move)

        return game.move_troops_after_attack(query, troops_to_move)
    
# Troop Defense Function --> For defending against enemy attacks (TAKEN FROM COMPLEX.PY)
def handle_defend(game: Game, bot_state: BotState, query: QueryDefend) -> MoveDefend:
    
    # We will always defend with the most troops that we can.
    move_attack = cast(MoveAttack, game.state.recording[query.move_attack_id])
    defending_territory = move_attack.defending_territory
    
    # We can only defend with up to 2 troops, and no more than we have stationed on the defending
    # territory.
    defending_troops = min(game.state.territories[defending_territory].troops, 2)
    return game.move_defend(query, defending_troops)

# Troop Fortification Function --> For moving troops after end of attack stage
def handle_fortify(game: Game, bot_state: BotState, query: QueryFortify) -> Union[MoveFortify, MoveFortifyPass]:
   
    # Obtain owned and bordering territories
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    my_border_territories = game.state.get_all_border_territories(game.state.get_territories_owned_by(game.state.me.player_id))

    # Obtain territories that are not borders
    unique_territories = []
    for territory in my_territories:
        if territory not in my_border_territories:
            unique_territories.append(territory)

    i=0
    non_borders_dict={}
    # Sort non-border territories in descending order of troops
    while i<len(unique_territories):
        troops=game.state.territories[unique_territories[i]].troops
        non_borders_dict[unique_territories[i]]=troops
        i+=1

    reverse_order_with_troops = sorted(non_borders_dict.items(), key=lambda item: item[1], reverse=True)

    sorted_non_borders=[]
    for border in reverse_order_with_troops:
        sorted_non_borders.append(border[0])

    i=0
    borders_dict={}
    # Sort border territories in ascending order of troops
    while i<len(my_border_territories):
        troops=game.state.territories[my_border_territories[i]].troops
        borders_dict[my_border_territories[i]]=troops
        i+=1

    order_w_troops=sorted(borders_dict.items(), key=lambda item: item[1])

    sorted_borders=[]
    for border in order_w_troops:
        sorted_borders.append(border[0])
    # Check if we can fortify from non-border to border territories using bfs function
    i=0
    while i<len(sorted_non_borders):
        j=0
        while j<len(sorted_borders):
            shortest_path = bfs(game,sorted_non_borders[i],set(my_territories),sorted_borders[j])
            if shortest_path ==True and game.state.territories[sorted_non_borders[i]].troops > 1:
                # Fortify target using all troops except one
                return game.move_fortify(query, sorted_non_borders[i], sorted_borders[j], game.state.territories[sorted_non_borders[i]].troops - 1)
            j+=1
        i+=1


    return game.move_fortify_pass(query)

# Breath-First Search Function --> For finding valid fortification path
def bfs(game: Game, source: int, my_owned_territories: Set[int], target: int) -> bool:
    
    # Initialize seen and parent dictionaries for owned territories
    seen: Dict[int, bool] = {territory: False for territory in my_owned_territories}
    parent: Dict[int, Optional[int]] = {territory: None for territory in my_owned_territories}

    # Mark the source as seen
    seen[source] = True

    # Use a deque for efficient popping from the front
    queue = deque([source])

    while queue:
        current = queue.popleft()

        # Get all adjacent territories
        for adjacent in game.state.get_all_adjacent_territories([current]):
            # Process only if adjacent territory is owned and not seen
            if adjacent in my_owned_territories and not seen[adjacent]:
                queue.append(adjacent)
                seen[adjacent] = True
                parent[adjacent] = current
                
    child = target
    if parent[child] == source:
        return True
    else:
        return False
    


# Main function call --> DO NOT EDIT
if __name__ == "__main__":
    main()