from inseeds.components import base


class Component(base.Component):
    """Model mixing class for farmer_management.
    This component initializes farmers in the model to make decisions
    on which management practices to apply to their fields.
    Two practices are available: conventional and conservation tillage.
    The theory of planned behaviour is used to model farmer decision-making.
    Two farmer AFTs are implemented, the traditionalist and the pioneer.
    """

    def init_farmers(self, farmer_class, **kwargs):
        """Initialize farmers."""
        farmers = []

        # Debug: Check if world has networks
        print(f"DEBUG: World has acquaintance_network: {hasattr(self.world, 'acquaintance_network')}")
        print(f"DEBUG: World has group_membership_network: {hasattr(self.world, 'group_membership_network')}")
        if hasattr(self.world, 'acquaintance_network'):
            print(f"DEBUG: acquaintance_network type: {type(self.world.acquaintance_network)}")
        if hasattr(self.world, 'group_membership_network'):
            print(f"DEBUG: group_membership_network type: {type(self.world.group_membership_network)}")

        for cell in self.world.cells:
            if cell.output.cftfrac.sum("band") == 0:
                continue

            farmer = farmer_class(cell=cell, model=self)
            farmers.append(farmer)

        farmers_sorted = sorted(farmers, key=lambda farmer: farmer.avg_hdate)
        for farmer in farmers_sorted:
            farmer.init_neighbourhood()

        # Create acquaintance networks within AFT groups
        self.create_aft_acquaintance_networks(farmers_sorted)

    def create_aft_acquaintance_networks(self, farmers):
        """Create acquaintance networks within AFT groups."""
        if not hasattr(self.world, 'acquaintance_network'):
            print("DEBUG: No acquaintance network available")
            return
            
        # Group farmers by AFT
        traditionalist_farmers = [f for f in farmers if f.aft.name == 'traditionalist']
        pioneer_farmers = [f for f in farmers if f.aft.name == 'pioneer']
        
        print(f"DEBUG: Creating acquaintance networks - {len(traditionalist_farmers)} traditionalists, {len(pioneer_farmers)} pioneers")
        
        # Add all farmers to the network
        for farmer in farmers:
            self.world.acquaintance_network.add_node(farmer)
        
        # Create edges between traditionalist farmers
        for i, farmer1 in enumerate(traditionalist_farmers):
            for farmer2 in traditionalist_farmers[i+1:]:
                self.world.acquaintance_network.add_edge(farmer1, farmer2)
                print(f"DEBUG: Added edge between traditionalist farmers {farmer1.cell.grid.cell.item()} and {farmer2.cell.grid.cell.item()}")
        
        # Create edges between pioneer farmers
        for i, farmer1 in enumerate(pioneer_farmers):
            for farmer2 in pioneer_farmers[i+1:]:
                self.world.acquaintance_network.add_edge(farmer1, farmer2)
                print(f"DEBUG: Added edge between pioneer farmers {farmer1.cell.grid.cell.item()} and {farmer2.cell.grid.cell.item()}")
        
        print(f"DEBUG: Created {len(traditionalist_farmers) * (len(traditionalist_farmers) - 1) // 2} traditionalist edges")
        print(f"DEBUG: Created {len(pioneer_farmers) * (len(pioneer_farmers) - 1) // 2} pioneer edges")

    def init_decision_makers(self, decision_maker_class, **kwargs):
        """Initialize decision makers."""
        decision_makers = []

        # Create a few decision makers at the world level (not tied to cells)
        num_decision_makers = getattr(
            self.config.coupled_config, 'num_decision_makers', 3
        )
        
        print(f"Creating {num_decision_makers} decision makers...")
        
        for i in range(num_decision_makers):
            decision_maker = decision_maker_class(world=self.world, model=self)
            decision_makers.append(decision_maker)
            
        # Add decision makers to the world's individuals list
        for decision_maker in decision_makers:
            self.world.individuals.add(decision_maker)
            
        # Also store in world.decision_makers for the update method
        if not hasattr(self.world, 'decision_makers'):
            self.world.decision_makers = set()
        self.world.decision_makers.update(decision_makers)
            
        print(f"Added {len(decision_makers)} decision makers to world. Total individuals: {len(self.world.individuals)}")
        
        # Debug: check if decision makers are in the world
        dm_count = sum(1 for ind in self.world.individuals if ind.__class__.__name__ == "DecisionMaker")
        print(f"Debug: Found {dm_count} DecisionMaker instances in world.individuals")
        
        # Debug: check what types of individuals are in the world
        individual_types = {}
        for ind in self.world.individuals:
            class_name = ind.__class__.__name__
            individual_types[class_name] = individual_types.get(class_name, 0) + 1
        print(f"Debug: Individual types in world: {individual_types}")
        
        return decision_makers

    def init_lobby_groups(self, lobby_group_class, **kwargs):
        """Initialize lobby groups."""
        lobby_groups = []

        # Import AFT enum from farmer module
        from inseeds.components.farming.farmer import AFT

        print("Creating 2 lobby groups...")

        # Create two lobby groups - one for each AFT type
        traditionalist_group = lobby_group_class(
            world=self.world, 
            model=self, 
            aft_type=AFT.traditionalist
        )
        traditionalist_group.init_world_attributes()
        lobby_groups.append(traditionalist_group)

        pioneer_group = lobby_group_class(
            world=self.world, 
            model=self, 
            aft_type=AFT.pioneer
        )
        pioneer_group.init_world_attributes()
        lobby_groups.append(pioneer_group)
        
        # Add lobby groups to the world's individuals list
        for lobby_group in lobby_groups:
            self.world.individuals.add(lobby_group)
            
        # Also store in world.lobby_groups for the update method
        if not hasattr(self.world, 'lobby_groups'):
            self.world.lobby_groups = set()
        self.world.lobby_groups.update(lobby_groups)
        
        print(f"Added {len(lobby_groups)} lobby groups to world. Total individuals: {len(self.world.individuals)}")
        
        return lobby_groups

    def update(self, t):
        super().update(t)

        # Decision makers vote on subsidy plan changes
        self.update_subsidy_plan_vote()

        # Reset subsidies and budget at the start of each year
        self.world.shared_subsidy_budget = 0.0
        self.world.land_based_subsidies = 0.0
        self.world.practice_based_subsidies = 0.0
        for farmer in self.world.farmers:
            farmer.received_subsidy = 0.0

        # Calculate world total crop yield for shared budget calculation
        if self.world.farmers:
            world_total_crop_yield = sum(farmer.cropyield for farmer in self.world.farmers)
        else:
            world_total_crop_yield = 0.0
        
        # Calculate shared subsidy budget (40% of world total crop yield)
        budget_value = world_total_crop_yield * 0.4
        # Ensure it's a scalar value
        if hasattr(budget_value, 'item'):
            budget_value = budget_value.item()
        elif hasattr(budget_value, 'values'):
            budget_value = budget_value.values.item()
        
        self.world.shared_subsidy_budget = budget_value
        
        # Distribute subsidies to farmers using hybrid system
        self.distribute_subsidies_to_farmers()

        # Update farmers (after they receive subsidies)
        farmers_sorted = sorted(
            self.world.farmers, key=lambda farmer: farmer.avg_hdate
        )
        for farmer in farmers_sorted:
            farmer.update(t)

        # Update lobby groups
        lobby_groups_sorted = sorted(
            self.world.lobby_groups, 
            key=lambda lg: lg.lobby_group_id
        )
        for lobby_group in lobby_groups_sorted:
            lobby_group.update(t)

    def update_subsidy_plan_vote(self):
        """Update subsidy plan based on decision maker majority vote.
        
        Decision makers vote based on their belief values:
        - Negative beliefs (-5 to 0): Vote to decrease subsidy_plan (more land-based)
        - Positive beliefs (0 to 5): Vote to increase subsidy_plan (more practice-based)
        - Belief = 0: Indifferent (no vote)
        
        Maximum change per year: ±0.5
        Ties result in no change
        """
        if not hasattr(self.world, 'decision_makers') or not self.world.decision_makers:
            return
            
        current_plan = self.world.subsidy_plan
        print(f"DEBUG: Current subsidy_plan: {current_plan}")
        
        # Count votes
        decrease_votes = 0  # Negative beliefs
        increase_votes = 0  # Positive beliefs
        indifferent_votes = 0  # Belief = 0
        
        for dm in self.world.decision_makers:
            belief = dm.belief_value
            print(f"DEBUG: Decision maker {dm.decision_maker_id} has belief: {belief}")
            
            if belief < 0:
                decrease_votes += 1
                print(f"DEBUG: DM {dm.decision_maker_id} votes DECREASE (belief: {belief})")
            elif belief > 0:
                increase_votes += 1
                print(f"DEBUG: DM {dm.decision_maker_id} votes INCREASE (belief: {belief})")
            else:
                indifferent_votes += 1
                print(f"DEBUG: DM {dm.decision_maker_id} is INDIFFERENT (belief: {belief})")
        
        print(f"DEBUG: Vote count - Decrease: {decrease_votes}, Increase: {increase_votes}, Indifferent: {indifferent_votes}")
        
        # Determine outcome
        if decrease_votes > increase_votes:
            # Majority wants to decrease (more land-based subsidies)
            new_plan = max(-5.0, current_plan - 0.5)
            change = new_plan - current_plan
            print(f"DEBUG: DECREASE wins. Changing subsidy_plan from {current_plan} to {new_plan} (change: {change})")
            self.world.subsidy_plan = new_plan
            
        elif increase_votes > decrease_votes:
            # Majority wants to increase (more practice-based subsidies)
            new_plan = min(5.0, current_plan + 0.5)
            change = new_plan - current_plan
            print(f"DEBUG: INCREASE wins. Changing subsidy_plan from {current_plan} to {new_plan} (change: {change})")
            self.world.subsidy_plan = new_plan
            
        else:
            # Tie or no majority - no change
            print(f"DEBUG: TIE or no majority. subsidy_plan stays at {current_plan}")
            print(f"DEBUG: No change to subsidy_plan")

    def distribute_subsidies_to_farmers(self):
        """Distribute the shared subsidy budget to farmers using hybrid system.
        
        The subsidy_plan parameter controls the distribution:
        -5: 100% land-based (proportional to crop land area)
        -2.5: 75% land-based, 25% practice-based
        0: 50% land-based, 50% practice-based
        2.5: 25% land-based, 75% practice-based
        5: 100% practice-based (only conservation tillage farmers)
        """
        if not self.world.farmers or self.world.shared_subsidy_budget <= 0:
            return
            
        # Get subsidy plan value (-5 to 5)
        subsidy_plan = self.world.subsidy_plan
        
        # Calculate weights for land-based vs practice-based subsidies
        # Convert from -5..5 range to 0..1 range for land-based weight
        land_weight = (5.0 - subsidy_plan) / 10.0  # 1.0 at -5, 0.0 at 5
        practice_weight = 1.0 - land_weight  # 0.0 at -5, 1.0 at 5
        
        # Calculate total crop land area across all farmers
        total_crop_area = 0.0
        for farmer in self.world.farmers:
            area = farmer.cell.area
            # Convert xarray to scalar if needed
            if hasattr(area, 'item'):
                area = area.item()
            elif hasattr(area, 'values'):
                area = area.values.item()
            total_crop_area += area
            
        if total_crop_area <= 0:
            return
            
        # Count conservation tillage farmers (practice = 0)
        conservation_farmers = [f for f in self.world.farmers if hasattr(f, 'tillage') and f.tillage == 0]
        num_conservation = len(conservation_farmers)
        
        # Initialize subsidy tracking
        total_land_subsidies = 0.0
        total_practice_subsidies = 0.0
        
        # Distribute subsidies using hybrid system
        for farmer in self.world.farmers:
            total_subsidy = 0.0
            
            # Land-based subsidy component
            if land_weight > 0:
                area = farmer.cell.area
                # Convert xarray to scalar if needed
                if hasattr(area, 'item'):
                    area = area.item()
                elif hasattr(area, 'values'):
                    area = area.values.item()
                    
                farmer_land_share = area / total_crop_area
                land_subsidy = self.world.shared_subsidy_budget * land_weight * farmer_land_share
                total_subsidy += land_subsidy
                total_land_subsidies += land_subsidy
            
            # Practice-based subsidy component
            if practice_weight > 0 and num_conservation > 0:
                # Check if farmer practices conservation tillage
                if hasattr(farmer, 'tillage') and farmer.tillage == 0:
                    # Distribute practice-based subsidies equally among conservation farmers
                    practice_subsidy = self.world.shared_subsidy_budget * practice_weight / num_conservation
                    total_subsidy += practice_subsidy
                    total_practice_subsidies += practice_subsidy
            
            # Store the total subsidy amount
            farmer.received_subsidy = total_subsidy
        
        # Update world subsidy tracking
        self.world.land_based_subsidies = total_land_subsidies
        self.world.practice_based_subsidies = total_practice_subsidies
        
 
        



