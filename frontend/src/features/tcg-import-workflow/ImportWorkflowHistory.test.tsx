import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ImportWorkflowPanel } from "./ImportWorkflowPanel";
import { useImportWorkflow } from "./useImportWorkflow";
import { useImportStageDetails } from "./useImportStageDetails";
vi.mock("./useImportWorkflow", () => ({useImportWorkflow:vi.fn()}));
vi.mock("./useImportStageDetails", () => ({useImportStageDetails:vi.fn()}));
vi.mock("./ExtractionAttemptHistory", () => ({ExtractionAttemptHistory: () => null}));
beforeEach(async () => {
 await i18n.changeLanguage("en");
 vi.mocked(useImportWorkflow).mockReturnValue({progress:{scope:{type:"import",import_job_id:"a"},as_of:"2026-09-14T00:00:00Z",coverage:"complete",review_status:"ok",reason:null,messages:{unit:"source_message",total:1},extraction:{unit:"extraction_job",total:1,completed:1,succeeded:0,empty:0,failed:1,pending:0,running:0,unknown:0},analysis:{unit:"extraction_item",total:0}},items:null,error:null,loading:false,refresh:vi.fn(),lastAsOf:null} as ReturnType<typeof useImportWorkflow>);
});
afterEach(cleanup);
it.each(["done","running","pending","empty"])("does not show failure text for %s rows", status => {
 vi.mocked(useImportStageDetails).mockReturnValue({rows:[{id:"job",source_message_id:"source",status,item_count:0,supplier_name:null,raw_text:"",error_reason_code:null}],loading:false,error:null,coverage:"complete",total:1,asOf:null,refresh:vi.fn()} as unknown as ReturnType<typeof useImportStageDetails>);
 render(<ImportWorkflowPanel importJobId="a"/>);
 fireEvent.click(screen.getByRole("button",{name:i18n.t("pmgWorkflow.errorAction",{count:1})}));
 expect(screen.queryByText(i18n.t("pmgWorkflow.errorUnknown"))).toBeNull();
 expect(screen.queryByText(i18n.t("pmgWorkflow.errorNext"))).toBeNull();
});
