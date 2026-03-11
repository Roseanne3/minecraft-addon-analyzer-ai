import os
from extractor import scan_file_tree
from json_validator import validate_json_file
from manifest_checker import check_manifest
from behavior_checker import check_behavior_pack
from resource_checker import check_resource_pack
from dependency_checker import check_dependencies
from performance_checker import check_performance
from ai_analyzer import analyze_with_ai


def find_pack_dirs(addon_path: str):
    """Locate behavior_packs and resource_packs directories."""
    bp_paths = []
    rp_paths = []
    manifest_paths = []

    for root, dirs, files in os.walk(addon_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for d in dirs:
            lower = d.lower()
            full = os.path.join(root, d)
            if "behavior" in lower:
                bp_paths.append(full)
            elif "resource" in lower or "texture" in lower:
                rp_paths.append(full)
        for f in files:
            if f == "manifest.json":
                manifest_paths.append(os.path.join(root, f))

    return bp_paths, rp_paths, manifest_paths


def compute_score(issues: list) -> float:
    """Compute addon quality score from 0-100."""
    score = 100.0
    deductions = {"error": 10, "warning": 3, "info": 0.5}
    for issue in issues:
        sev = issue.get("severity", "info")
        score -= deductions.get(sev, 0)
    return max(0.0, min(100.0, round(score, 1)))


def scan_addon(addon_path: str) -> dict:
    """Run full analysis on extracted addon. Returns structured results."""
    results = {
        "files": [],
        "structure_issues": [],
        "manifest_issues": [],
        "json_issues": [],
        "behavior_issues": [],
        "resource_issues": [],
        "dependency_issues": [],
        "performance_issues": [],
        "ai_suggestions": [],
        "all_issues": [],
        "score": 100.0,
        "stats": {}
    }

    if not os.path.isdir(addon_path):
        results["structure_issues"].append({
            "severity": "error",
            "message": "Addon directory not found",
            "auto_fixable": False,
        })
        return results

    # Scan file tree
    file_list = scan_file_tree(addon_path)
    results["files"] = file_list

    # Structure check
    bp_paths, rp_paths, manifest_paths = find_pack_dirs(addon_path)

    has_manifest = len(manifest_paths) > 0
    has_bp = len(bp_paths) > 0
    has_rp = len(rp_paths) > 0

    if not has_manifest:
        results["structure_issues"].append({
            "severity": "error",
            "message": "No manifest.json found in addon",
            "fix_suggestion": "Create a manifest.json at the root of your behavior or resource pack",
            "auto_fixable": False,
        })
    if not has_bp:
        results["structure_issues"].append({
            "severity": "warning",
            "message": "No behavior_packs folder found",
            "fix_suggestion": "Create a 'behavior_packs' folder for entity/item definitions",
            "auto_fixable": False,
        })
    if not has_rp:
        results["structure_issues"].append({
            "severity": "warning",
            "message": "No resource_packs folder found",
            "fix_suggestion": "Create a 'resource_packs' folder for textures/models",
            "auto_fixable": False,
        })

    # Manifest analysis
    for mp in manifest_paths:
        rel = os.path.relpath(mp, addon_path)
        manifest_result = check_manifest(mp)
        for issue in manifest_result["issues"]:
            issue["file_path"] = issue.get("file_path", rel)
            issue["report_type"] = "manifest"
        results["manifest_issues"].extend(manifest_result["issues"])

    # JSON validation on all JSON files
    for f in file_list:
        if f["extension"] == ".json":
            json_result = validate_json_file(f["full_path"])
            for issue in json_result["issues"]:
                issue["file_path"] = issue.get("file_path", f["relative_path"])
                issue["report_type"] = "json"
            results["json_issues"].extend(json_result["issues"])

    # Behavior pack analysis
    for bp in bp_paths:
        bp_issues = check_behavior_pack(bp)
        for issue in bp_issues:
            issue["report_type"] = "behavior"
        results["behavior_issues"].extend(bp_issues)

    # Resource pack analysis
    for rp in rp_paths:
        rp_issues = check_resource_pack(rp)
        for issue in rp_issues:
            issue["report_type"] = "resource"
        results["resource_issues"].extend(rp_issues)

    # Dependency analysis
    dep_issues = check_dependencies(addon_path)
    for issue in dep_issues:
        issue["report_type"] = "dependency"
    results["dependency_issues"].extend(dep_issues)

    # Performance analysis
    perf_issues = check_performance(addon_path, file_list)
    for issue in perf_issues:
        issue["report_type"] = "performance"
    results["performance_issues"].extend(perf_issues)

    # AI analysis
    ai_issues = analyze_with_ai(file_list, addon_path)
    for issue in ai_issues:
        issue["report_type"] = "ai"
    results["ai_suggestions"].extend(ai_issues)

    # Compile all issues
    all_issues = (
        results["structure_issues"]
        + results["manifest_issues"]
        + results["json_issues"]
        + results["behavior_issues"]
        + results["resource_issues"]
        + results["dependency_issues"]
        + results["performance_issues"]
        + results["ai_suggestions"]
    )
    results["all_issues"] = all_issues

    # Compute stats
    by_type = {}
    for issue in all_issues:
        rt = issue.get("report_type", "other")
        by_type[rt] = by_type.get(rt, 0) + 1

    results["stats"] = {
        "files_scanned": len(file_list),
        "total_issues": len(all_issues),
        "errors": sum(1 for i in all_issues if i.get("severity") == "error"),
        "warnings": sum(1 for i in all_issues if i.get("severity") == "warning"),
        "info": sum(1 for i in all_issues if i.get("severity") == "info"),
        "by_type": by_type,
        "has_behavior_pack": has_bp,
        "has_resource_pack": has_rp,
        "has_manifest": has_manifest,
        "file_types": {},
    }

    # File type breakdown
    type_counts = {}
    for f in file_list:
        t = f["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    results["stats"]["file_types"] = type_counts

    results["score"] = compute_score(all_issues)
    return results
