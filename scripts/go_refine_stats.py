import requests
import json
import sys, getopt, os

import go_stats
import go_ontology_changes
import go_annotation_changes



def print_help():
    print('\nUsage: python go_refine.py -g <golr_url> -d <release_date> -c <current_obo_url> -p <previous_obo_url> -o <output_rep>\n')


def main(argv):
    golr_url = ''
    current_obo_url = ''
    previous_obo_url = ''    
    output_rep = ''
    release_date = ''

    if len(argv) < 10:
        print_help()
        sys.exit(2)

    try:
        opts, argv = getopt.getopt(argv,"g:c:p:o:d:",["golrurl=", "cobo=", "pobo=", "orep=", "date="])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt in ("-g", "--golrurl"):
            golr_url = arg
        elif opt in ("-c", "--cobo"):
            current_obo_url = arg
        elif opt in ("-p", "--pobo"):
            previous_obo_url = arg
        elif opt in ("-o", "--orep"):
            output_rep = arg
        elif opt in ("-d", "--date"):
            release_date = arg

    if not output_rep.endswith("/"):
        output_rep += "/"

    if not os.path.exists(output_rep):
        os.mkdir(output_rep)


    # 1 - Executing go_stats script
    print("\n\n1a - EXECUTING GO_STATS SCRIPT (INCLUDING PROTEIN BINDING)...\n")
    json_stats = go_stats.compute_stats(golr_url, release_date)
    # data = None
    # with open('newtest/go-stats.json', 'r') as myfile:
    #     data=myfile.read()
    # json_stats = json.loads(data)


    print("DONE.")

    print("\n\n1b - EXECUTING GO_STATS SCRIPT (EXCLUDING PROTEIN BINDING)...\n")
    json_stats_no_pb = go_stats.compute_stats(golr_url, release_date, True)
    # with open('newtest/go-stats-no-pb.json', 'r') as myfile:
    #     data=myfile.read()
    # json_stats_no_pb = json.loads(data)    
    print("DONE.")


    # 2 - Executing go_ontology_changes script
    print("\n\n2 - EXECUTING GO_ONTOLOGY_CHANGES SCRIPT...\n")
    # with open('newtest/go-ontology-changes.json', 'r') as myfile:
    #     data=myfile.read()
    # json_onto_changes = json.loads(data)
    
    json_onto_changes = go_ontology_changes.compute_changes(current_obo_url, previous_obo_url)
    go_annotation_changes.write_json(output_rep + "go-ontology-changes.json", json_onto_changes)

    tsv_onto_changes = go_ontology_changes.create_text_report(json_onto_changes) 
    go_annotation_changes.write_text(output_rep + "go-ontology-changes.tsv", tsv_onto_changes)
    print("DONE.")


    # 4 - Refining go-stats with ontology stats
    print("\n\n4 - EXECUTING GO_REFINE_STATS SCRIPT...\n")

    ontology = json_onto_changes["summary"]["current"].copy()
    del ontology["release_date"]
    ontology["changes_created_terms"] = json_onto_changes["summary"]["changes"]["created_terms"]
    ontology["changes_valid_terms"] = json_onto_changes["summary"]["changes"]["valid_terms"]
    ontology["changes_obsolete_terms"] = json_onto_changes["summary"]["changes"]["obsolete_terms"]
    ontology["changes_merged_terms"] = json_onto_changes["summary"]["changes"]["merged_terms"]

    json_stats = {
        "release_date" : json_stats["release_date"],
        "ontology" : ontology,
        "annotations" : json_stats["annotations"],
        "taxa" : json_stats["taxa"],
        "bioentities" : json_stats["bioentities"],
        "references" : json_stats["references"]
    }
    go_stats.write_json(output_rep + "go-stats.json", json_stats)


    json_stats_no_pb = {
        "release_date" : json_stats_no_pb["release_date"],
        "ontology" : ontology,
        "annotations" : json_stats_no_pb["annotations"],
        "taxa" : json_stats_no_pb["taxa"],
        "bioentities" : json_stats_no_pb["bioentities"],
        "references" : json_stats_no_pb["references"]
    }
    go_stats.write_json(output_rep + "go-stats-no-pb.json", json_stats_no_pb)


    annotations_by_reference_genome = json_stats["annotations"]["by_model_organism"]
    for taxon in annotations_by_reference_genome:
        for ecode in annotations_by_reference_genome[taxon]["by_evidence"]:
            annotations_by_reference_genome[taxon]["by_evidence"][ecode]["B"] = json_stats["annotations"]["by_model_organism"][taxon]["by_evidence"][ecode]["F"] - json_stats_no_pb["annotations"]["by_model_organism"][taxon]["by_evidence"][ecode]["F"]
        for ecode in annotations_by_reference_genome[taxon]["by_evidence_cluster"]:
            annotations_by_reference_genome[taxon]["by_evidence_cluster"][ecode]["B"] = json_stats["annotations"]["by_model_organism"][taxon]["by_evidence_cluster"][ecode]["F"] - json_stats_no_pb["annotations"]["by_model_organism"][taxon]["by_evidence_cluster"][ecode]["F"]

    bioentities_by_reference_genome = { }
    for taxon in go_stats.reference_genomes_ids:
        key = go_stats.taxon_label(taxon)
        bioentities_by_reference_genome[key] = json_stats["bioentities"]["by_filtered_taxon"]["cluster"][key] if key in json_stats["bioentities"]["by_filtered_taxon"]["cluster"] else { }
        # TODO: we don't have a way to filter on bioentity documents without direct annotations to PB ?
        # for btype in bioentities_by_reference_genome[key]:
        #     val = json_stats_no_pb["bioentities"]["by_filtered_taxon"]["cluster"][key]["F"] if (key in json_stats_no_pb["bioentities"]["by_filtered_taxon"]["cluster"] and "F" in json_stats_no_pb["bioentities"]["by_filtered_taxon"]["cluster"][key]) else 0
        #     bioentities_by_reference_genome[key][btype]["B"] = bioentities_by_reference_genome[key][btype]["F"] - val

    references_by_reference_genome = { }
    for taxon in go_stats.reference_genomes_ids:
        key = go_stats.taxon_label(taxon)
        references_by_reference_genome[key] = json_stats["references"]["all"]["by_filtered_taxon"][key] if key in json_stats["references"]["all"]["by_filtered_taxon"] else { }

    pmids_by_reference_genome = { }
    for taxon in go_stats.reference_genomes_ids:
        key = go_stats.taxon_label(taxon)
        pmids_by_reference_genome[key] = json_stats["references"]["pmids"]["by_filtered_taxon"][key] if key in json_stats["references"]["pmids"]["by_filtered_taxon"] else { }
        
    json_stats_summary = {
        "release_date" : json_stats["release_date"],
        "ontology" : ontology,
        "annotations" : {
            "total" : json_stats["annotations"]["total"],
            "total_no_pb" : json_stats_no_pb["annotations"]["total"],
            "by_aspect" : {
                "P" : json_stats["annotations"]["by_aspect"]["P"],
                "F" : json_stats["annotations"]["by_aspect"]["F"],
                "C" : json_stats["annotations"]["by_aspect"]["C"],
                "B" : json_stats["annotations"]["by_aspect"]["F"] - json_stats_no_pb["annotations"]["by_aspect"]["F"]
            },
            "by_bioentity_type_cluster" : json_stats["annotations"]["by_bioentity_type"]["cluster"],
            "by_bioentity_type_cluster_no_pb" : json_stats_no_pb["annotations"]["by_bioentity_type"]["cluster"],
            "by_evidence_cluster" : json_stats["annotations"]["by_evidence"]["cluster"],
            "by_evidence_cluster_no_pb" : json_stats_no_pb["annotations"]["by_evidence"]["cluster"],
            "by_model_organism" : annotations_by_reference_genome
        },
        "taxa" : {
            "total" : json_stats["taxa"]["total"],
            "filtered" : json_stats["taxa"]["filtered"],
        },
        "bioentities" : {
            "total" : json_stats["bioentities"]["total"],
            "total_no_pb" : json_stats_no_pb["bioentities"]["total"],
            "by_type_cluster" : json_stats["bioentities"]["by_type"]["cluster"],
            "by_type_cluster_no_pb" : json_stats_no_pb["bioentities"]["by_type"]["cluster"],
            "by_model_organism" : bioentities_by_reference_genome
        },
        "references" : {
            "all" : {
                "total" : json_stats["references"]["all"]["total"],
                "total_no_pb" : json_stats_no_pb["references"]["all"]["total"],
                "by_model_organism" : references_by_reference_genome
            },
            "pmids" : {
                "total" : json_stats["references"]["pmids"]["total"],
                "total_no_pb" : json_stats_no_pb["references"]["pmids"]["total"],
                "by_model_organism" : pmids_by_reference_genome
            }
        },
    }
    go_stats.write_json(output_rep + "go-stats-summary.json", json_stats_summary)

    print("DONE.")





if __name__ == "__main__":
   main(sys.argv[1:])
   