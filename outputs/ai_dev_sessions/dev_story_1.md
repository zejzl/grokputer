### Story 1: Enhance Consistency Checks for Validator

**User Story**: As a developer, I want automated PRD cross-referencing in Validator so that stories align with planning docs, reducing context loss.

**Why (Business Value)**: Ensures high fidelity between Phase 1 PRD/arch and Phase 2 stories; catches inconsistencies early (e.g., missing scalability refs). Ties to Pantheon safety goal: 95%+ validation score.

**Acceptance Criteria**:
- Validator processes stories and PRD/arch, scoring keyword/semantic overlap >80%.
- Issues listed if score <80% (e.g., "Missing PRD reference in Story 2").
- Re-generation triggered if invalid (human or auto-feedback loop).
- Hash integrity check: MD5 of story content matches Redis stored hash.
- Offline fallback: Use cached templates if API fails.

**Implementation Steps**:
1. **Update Validator.process()**: Add cross-ref logic.
   ```python
   def cross_ref_docs(story_text: str, prd_text: str, arch_text: str) -> float:
       # Simple keyword overlap (future: embeddings via sentence-transformers)
       story_words = set(story_text.lower().split())
       prd_words = set(prd_text.lower().split())
       arch_words = set(arch_text.lower().split())
       overlap_prd = len(story_words & prd_words) / len(prd_words or [1])
       overlap_arch = len(story_words & arch_words) / len(arch_words or [1])
       return (overlap_prd + overlap_arch) / 2 * 100  # Score %
   
   # In process:
   score = cross_ref_docs(story_content, docs['prd.md'], docs['arch.md'])
   if score < 80:
       issues.append(f"Low overlap: {score}% - Add refs to PRD/Arch")
   ```
2. **Integrate Perceptual Hashing**: Enhance _save_doc for diff detection.
   ```python
   import hashlib
   def validate_hash(content: str, stored_hash: str) -> bool:
       current = hashlib.md5(content.encode()).hexdigest()
       return current == stored_hash
   
   # In Validator:
   for story in stories:
       if not validate_hash(story['content'], story['hash']):
           issues.append("Hash mismatch - content tampered?")
   ```
3. **Bus Notification**: Publish validation results for Analyzer.
   ```python
   await self.bus.publish("validation_complete", {"score": score, "issues": issues})
   ```
4. **Error Handling**: If low score, prompt re-run Phase 2 with feedback.
   ```python
   if not valid:
       feedback = f"Fix: {issues}"
       phase1_docs['feedback'] = feedback  # Append for Scrum Master
   ```

**Test Outlines**:
- **Unit Tests** (pytest test_validator.py):
  ```python
  def test_cross_ref_high_overlap():
      story = "Implement PRD requirements with Arch scalability."
      prd = "PRD requirements include validation."
      arch = "Arch scalability for agents."
      score = cross_ref_docs(story, prd, arch)
      assert score > 80
  
  def test_hash_mismatch():
      assert not validate_hash("changed content", "original_hash")
  ```
- **Integration Tests**: End-to-end workflow with mock low-score story → triggers re-gen.
- **Edge**: Offline mode - load cached validation templates; large docs chunked.

**Architectural Ties** (Reference Phase 1 Docs):
- **PRD.md**: High priority (from PM: "Enhance Validator as core safety"); risks mitigated (API fails → offline).
- **Arch.md**: Scalable via bus (publish issues for swarm handling); Redis for hash storage (eternal integrity).
- Dependencies: BaseAgent.process for message passing; GrokClient (temp=0.2 for consistency).

**Estimated Effort**: 4 hours (2 coding, 1 testing, 1 docs). Priority: High (Pantheon safety).

---

Generated in Session: 20251111_0405XX | ZA GROKA.