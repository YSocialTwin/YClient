import json
import os
import shutil
import sys

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(SCRIPT_DIR))

    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument(
        "-c",
        "--config_file",
        default="config_files/config.json",
        help="JSON file describing the simulation configuration",
    )
    parser.add_argument(
        "-f",
        "--feeds",
        default="config_files/feed_small.json",
        help="JSON file containing rss feed categorized",
    )
    parser.add_argument(
        "-p",
        "--prompts",
        default="config_files/prompts.json",
        help="JSON file containing LLM prompts",
    )
    parser.add_argument(
        "-a", "--agents", default=None, help="JSON file with pre-existing agents"
    )
    parser.add_argument(
        "-o", "--owner", default="admin", help="Simulation owner username"
    )
    parser.add_argument(
        "-r",
        "--reset",
        default=False,
        help="Boolean. Whether to reset the experiment status. Default False",
    )
    parser.add_argument(
        "-n",
        "--news",
        default=False,
        help="Boolean. Whether to reload the rss feeds. Default False",
    )
    parser.add_argument(
        "-x",
        "--crecsys",
        default="ReverseChronoFollowersPopularity",
        help="Name of the content recsys to be used. Options: ...",
    )
    parser.add_argument(
        "-y",
        "--frecsys",
        default="PreferentialAttachment",
        help="Name of the follower recsys to be used. Options: ...",
    )

    parser.add_argument(
        "-g",
        "--graph",
        default=None,
        help="Name of the graph file (CSV format, number of nodes equal to the starting agents) "
        "to be used for the simulation",
    )
    
    parser.add_argument(
        "-l",
        "--log_file",
        default=None,
        help="Path to the log file for agent execution time tracking. "
             "Defaults to 'experiments/{simulation_name}_client.log'",
    )

    args = parser.parse_args()

    agents_owner = args.owner
    config_file = args.config_file
    agents_file = args.agents
    rss_feeds = args.feeds
    prompts_file = args.prompts
    graph_file = args.graph

    # get simulation client and name
    config = json.load(open(config_file, "r"))
    client_name = config["simulation"]["client"]
    simulation_name = config["simulation"]["name"]

    # agent file output
    output = f"experiments{os.sep}{simulation_name}_agents.json"

    # set the current config file (needed to generate the database)
    shutil.copyfile(config_file, f"experiments{os.sep}current_config.json")

    import y_client.clients
    import y_client.recsys

    if not os.path.exists("experiments"):
        os.mkdir("experiments")

    # get recommender systems
    content_recsys = getattr(y_client.recsys, args.crecsys)()
    follow_recsys = getattr(y_client.recsys, args.frecsys)(leaning_bias=1.5)

    ExperimentClass = getattr(y_client.clients, client_name)

    if client_name == "YClientWeb":
        data_base_path = os.path.abspath(os.path.dirname(prompts_file))
        if graph_file:
            graph_file = os.path.abspath(graph_file)
            graph_target = os.path.join(data_base_path, os.path.basename(graph_file))
            if graph_target != graph_file:
                shutil.copyfile(graph_file, graph_target)
            graph_file = os.path.basename(graph_target)

        experiment = ExperimentClass(
            config_file=config,
            data_base_path=f"{data_base_path}{os.sep}",
            agents_filename=agents_file,
            owner=agents_owner,
            agents_output=output,
            first_run=bool(args.agents is None),
            network=graph_file,
            log_file=args.log_file,
        )
    else:
        experiment = ExperimentClass(
            config_file,
            prompts_file,
            agents_filename=agents_file,
            owner=agents_owner,
            agents_output=output,
            graph_file=graph_file,
            log_file=args.log_file,
        )

    if args.reset:
        experiment.reset_experiment()
    if args.news:
        experiment.reset_news_db()
        experiment.load_rrs_endpoints(rss_feeds)

    experiment.set_recsys(content_recsys, follow_recsys)

    if args.agents is None:
        if client_name == "YClientWeb":
            experiment.read_agents()
        else:
            experiment.create_initial_population()
    else:
        experiment.load_existing_agents(args.agents)

    if graph_file and hasattr(experiment, "add_network"):
        experiment.add_network()

    if client_name == "YClientWeb":
        experiment.save_agents(output)
    else:
        experiment.save_agents()
    experiment.run_simulation()
